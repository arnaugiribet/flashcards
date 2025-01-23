import logging

# Logger set up
logger = logging.getLogger("src/backend/usage_limits.py")
logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s: %(message)s")
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

def assert_input_length(input_text):
    logger.info('Checking length of input text...')
    pass
def assert_enough_tokens(user, input_text):
    logger.info('Checking user has enough tokens to proceed...')
    pass