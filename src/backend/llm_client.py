import openai  # Or any other library you're using

class LLMClient:
    def __init__(self, api_key, model="gpt-3.5-turbo"):
        """
        Initialize the LLMClient with API key and model.
        """
        self.api_key = api_key
        self.model = model
        openai.api_key = api_key

    def query(self, prompt, system_message="Transform this text into a flashcard for studying. A question and an answer. Return it in CSV format."):
        """
        Send a prompt to the LLM and return the response content.
        """
        try:
            completion = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ]
                )

            return (completion.choices[0].message.content)

        except Exception as e:
            raise RuntimeError(f"Error querying the LLM: {e}")
