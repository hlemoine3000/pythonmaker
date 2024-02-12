import logging

import openai

class OpenAIWrapper:
    def __init__(self, log_file='openai_log.txt'):
        """
        Initialize the wrapper with the OpenAI API key and set up logging.
        """
        self._openai_client = openai.OpenAI()
        # Set up a dedicated logger for this class
        self.logger = logging.getLogger('OpenAIWrapper')
        self.logger.setLevel(logging.DEBUG)
        file_handler = logging.FileHandler(log_file)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        # Prevent logging from propagating to the root logger
        self.logger.propagate = False

    def complete(self, messages, model: str, temperature: float = 0.5, **kwargs) -> str:
        """Generate text completion and log the prompt and response.
        """
        try:
            response = self._openai_client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                **kwargs
            )
            response_content = response.choices[0].message.content
            self.logger.info(f"Prompt:\n{messages}\nResponse:\n{response_content}")
            return response_content
        except Exception as e:
            self.logger.error(f"Error generating completion: {e}")
            raise e