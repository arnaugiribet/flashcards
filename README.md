# flashcards

## Setup Instructions

1. **Create the Conda Environment**  
   To create the Conda environment named `flash` with Python 3.10, run the following command:
   ```bash
   conda create --name flash python=3.10
   conda activate flash
   ```
   
2. **Install the requirements**
   Install the required dependencies by running:
   ```bash
   pip install -r requirements.txt
   ```
3. **If you cannot access port 8000:
   ```bash
   FPORT=8000
   WORKSPACE_BASE_URL=apm0074851-rnaseq-amer01/ag-scrna
   curl -X POST -d "prefix=${WORKSPACE_BASE_URL}/port/${FPORT}" -d "strip_prefix=true" http://localhost:9001/${FPORT}
   ```
   # then the url will be: https://apps.workbench.p171649450587.aws-amer.sanofi.com/apm0074851-rnaseq-amer01/ag-scrna/port/8000/

   
   