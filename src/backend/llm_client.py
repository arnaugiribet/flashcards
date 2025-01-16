import openai  # Or any other library you're using
import logging

class LLMClient:
    def __init__(self, api_key, model="gpt-3.5-turbo"):
        """
        Initialize the LLMClient with API key and model.
        """
        self.api_key = api_key
        self.model = model
        openai.api_key = api_key

        # Logger set up
        self.logger = logging.getLogger("src/backend/llm_client.py")
        self.logger.setLevel(logging.DEBUG)
        console_handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s: %(message)s")
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

    def query(self, prompt, system_message):
        """
        Send a prompt to the LLM and return the response content.
        """
        self.logger.debug("Starting call to LLM...")
        try:
            completion = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ]
                )
            response = completion.choices[0].message.content

        except Exception as e:
            raise RuntimeError(f"Error querying the LLM: {e}")
        
        self.logger.debug(f"System message:\n{repr(system_message)}\nPrompt:\n{repr(prompt)}")
        self.logger.debug(f"Response from the LLM:\n{repr(response)}\n")
        return (response)