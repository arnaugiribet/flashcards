import logging

# Logger set up
logger = logging.getLogger("src/backend/usage_limits.py")
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s: %(message)s")
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

def assert_input_length(input_text):
    logger.info('Checking length of input text...')
    len_input_text = len(input_text)
    logger.debug(f'The text has {len_input_text} characters')
    if len_input_text > 30000:
        raise ValueError(f"Input text length {len(input_text)} exceeds maximum allowed length of 30000 characters")

def assert_enough_tokens(user, input_text):
    logger.info('Checking user has enough tokens to proceed...')
    pass