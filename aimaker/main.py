import openai
import asyncio
import aiofiles
import subprocess
import logging
import os
import time

from aimaker import utils
from aimaker import client


type MessagesStack = list[dict[str, str]]


class PythonFunction:
    def __init__(self, name: str, content: str):
        self.name = name
        self.content = content


class PythonFunctionSuite:
    def __init__(self, function: PythonFunction, test: PythonFunction):
        self.function = function
        self.test = test


class PythonFileScript:
    def __init__(
        self,
        openai_client: client.OpenAIWrapper,
        functions: list[PythonFunctionSuite],
        module_name: str,
    ):
        self.openai_client = openai_client
        self.functions = functions
        self.module_name = module_name
        self._logger = logging.getLogger(__name__)

    async def generate_python_code(
        self, instructions_input: MessagesStack
    ) -> PythonFunction:
        """Generates a Python script based on a given prompt."""
        response_content = self.openai_client.complete(instructions_input, "gpt-4", temperature=0.5)
        python_script = utils.extract_substring(response_content, "```python", "```")

        try:
            function_name = utils.extract_single_function_name(python_script)
        except Exception as e:
            function_name = "lol"
            self._logger.error(f"Error extracting function name: {e}")
            self._logger.error(f"Python script: {python_script}")
        if function_name is None:
            raise ValueError(
                "The generated Python code does not contain exactly one function definition."
            )

        self._logger.info(f"Generated Python function: {function_name}")
        return PythonFunction(function_name, python_script)

    async def generate_python_function(self, function_goal: str) -> PythonFunction:
        """Generates a Python script based on a given prompt."""
        prompt = f"Write a Python function to {function_goal}. The code must be typed. The answer must only be the python code and nothing else."
        instructions_input = [
            {"role": "system", "content": "You are a python programmer."},
            {"role": "user", "content": prompt},
        ]
        return await self.generate_python_code(instructions_input)

    async def generate_python_test(
        self, function_to_test: PythonFunction, script_package_name: str
    ) -> PythonFunction:
        """Generates a Python test based on a given prompt."""
        prompt = f"Write a Python test for the function above. The code must be typed and shall use pytest parametric tests. The function must be called test_{function_to_test.name} The answer must only be the python code and nothing else."
        instructions_input = [
            {"role": "system", "content": "You are a python programmer."},
            {
                "role": "user",
                "content": f"The module can be imported with ```python\nfrom {script_package_name} import {self.module_name}\n```\nCode to test:\n```python\n{function_to_test.content}\n```",
            },
            {"role": "user", "content": prompt},
        ]
        return await self.generate_python_code(instructions_input)

    async def add_function(self, function_goal: str, script_package_name: str):
        python_function = await self.generate_python_function(function_goal)
        python_test = await self.generate_python_test(
            python_function, script_package_name
        )
        self.functions.append(PythonFunctionSuite(python_function, python_test))

    async def write_to_file(self, workspace: str, package_name: str):
        script_filepath = os.path.join(workspace, package_name, f"{self.module_name}.py")
        async with aiofiles.open(script_filepath, "w") as script_file:
            for function_set in self.functions:
                await script_file.write(function_set.function.content)
        test_filepath = os.path.join(workspace, "tests", f"test_{self.module_name}.py")
        async with aiofiles.open(test_filepath, "w") as script_file:
            for function_set in self.functions:
                await script_file.write(function_set.test.content)


class PythonPackage:
    _scripts: list[PythonFileScript]

    def __init__(
        self,
        workspace_directory: str = "workspace",
        backup_directory: str = "backup",
        package_name: str = "testpackage",
    ):
        self._openai_client = client.OpenAIWrapper()
        self._logger = logging.getLogger(__name__)
        self._workspace_directory = workspace_directory
        self._backup_directory = backup_directory
        self._package_name = package_name
        self._package_directory = os.path.join(self._workspace_directory, package_name)
        self._test_directory = os.path.join(self._workspace_directory, "tests")
        self._scripts = []
        self.init_workspace()

    def init_workspace(self):
        """Initializes the workspace directory."""
        os.makedirs(self._workspace_directory, exist_ok=True)
        # If the workscpace directory is not empty, move its contents to the backup directory
        if os.listdir(self._workspace_directory):
            backup_subdirectory = os.path.join(
                self._backup_directory, time.strftime("%Y%m%d-%H%M%S")
            )
            os.makedirs(backup_subdirectory)
            for filename in os.listdir(self._workspace_directory):
                source = os.path.join(self._workspace_directory, filename)
                destination = os.path.join(backup_subdirectory, filename)
                os.rename(source, destination)

        # Init package directory
        os.makedirs(self._package_directory, exist_ok=True)
        with open(os.path.join(self._package_directory, "__init__.py"), "w") as f:
            f.write("")
        # Init test directory
        os.makedirs(self._test_directory, exist_ok=True)
        with open(os.path.join(self._test_directory, "__init__.py"), "w") as f:
            f.write("")

    async def write_files(self):
        for script in self._scripts:
            await script.write_to_file(self._workspace_directory, self._package_name)

    async def execute_tests(self):
        await self.write_files()
        cmd = ["pytest", "tests"]
        self._logger.info(f"Executing Python tests: {' '.join(cmd)}")
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self._workspace_directory,
        )
        stdout, stderr = await process.communicate()

        self._logger.info(f"stdout:\n{stdout.decode()}")
        # if process.returncode == 0:
        #     return True, stdout.decode()
        # else:
        #     return False, stderr.decode()

    async def add_function(self, function_goal: str):
        """Create a python function and tests base on the prompt

        Args:
            prompt (str): prompt to create the function
        """
        my_script = PythonFileScript(self._openai_client, [], "main")
        await my_script.add_function(function_goal, self._package_name)
        self._scripts.append(my_script)


async def main():
    aimaker = PythonPackage()
    await aimaker.add_function("list all files in a directory")
    await aimaker.execute_tests()


# Run the main function
if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )
    asyncio.run(main())
