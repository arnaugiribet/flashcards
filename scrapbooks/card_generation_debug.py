#################################
## Setting up the debugging space
#################################

import os
import sys

# Add path so that modules are accessible
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from src.backend.flashcard_generator import FlashcardGenerator
from src.backend.llm_client import LLMClient
import logging
from django.conf import settings

# Logger set up
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s: %(message)s")
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Initialize modules
llm_api_key = os.getenv('LLM_API_KEY')
llm_client = LLMClient(llm_api_key)
generator = FlashcardGenerator(llm_client)

#################################
## DEBUGGING
#################################

response = '"¿Qué es el ordenamiento jurídico y qué regula?"\n"El ordenamiento jurídico regula la convivencia de las personas y siempre tiene contenido obligatorio."\n\n"¿Qué significa que una norma sea imperativa?"\n"Una norma imperativa es aquella que los sujetos no pueden modificar su contenido."\n\n"¿Qué son las normas jurídicas y cuándo se consideran como tales?"\n"Las normas jurídicas son aquellas impuestas coactivamente por los órganos competentes del estado y se consideran como tales cuando son mantenidas por el poder público."\n\n"¿Qué implica el principio de generalidad en una norma jurídica?"\n"El principio de generalidad implica que la norma afecta a un número determinado de personas, no a particulares."\n\n"¿En qué se diferencia una norma imperativa de una norma dispositiva?"\n"Una norma imperativa no puede ser modificada por los sujetos, mientras que una norma dispositiva se aplica si no hay pacto contrario de los sujetos."'

clean_response = generator.enforce_format(response)

flashcards = generator.create_flashcards_from_response(clean_response)
logger.debug(f"flashcards: {[flash.short_str() for flash in flashcards]}")
