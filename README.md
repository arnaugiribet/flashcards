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
   Then the url will be: https://apps.workbench.p171649450587.aws-amer.sanofi.com/apm0074851-rnaseq-amer01/ag-scrna/port/8000/

   ## Deployment Instructions - First time

1. **Log in to Heroku**
   ```bash
   heroku login
   ```

2. **Install dependencies if not there yet**
   ```bash
   pip install gunicorn whitenoise dj-database-url
   ```
3. **Add Procfile**
   In the same folder where manage.py is found, add a file called Procfile (no extension) with this content:
   ```plaintext
   web: gunicorn your_project_name.wsgi
   ```
4. **Handle Allowed Hosts**
   In settings.py, we will make the allowed hosts be read from .env

   ```python
   import environ
   # Initialize the environment values
   env = environ.Env()
   environ.Env.read_env() # read the .env file

   ALLOWED_HOSTS = env.list('ALLOWED_HOSTS')
   ```

   We will create an .env file in root, in the same folder we have manage.py
   Notice there is no space between the key, equal symbol and the string. Necessary.

   ```plaintext
   ALLOWED_HOSTS='*'
   ```

   Locally, this will allow us to have access to the app. To restrict it to our domain only for production, we will, in bash:

   ```bash
   heroku config:set ALLOWED_HOSTS=flash-app-040306dc86e6.herokuapp.com --app flash-app
   ```
   
   The app's domain is found with bash: heroku apps:info --app {YOUR_APP_NAME}

   Your list of apps names' can be found with bash: heroku apps

5. **Further date settings.py**
   
   ```python
   # Add info about database connection:
   import dj_database_url
   DATABASES = {
      'default': dj_database_url.config(conn_max_age=600, ssl_require=True)
   }

   # Configure static files to work with Heroku:
   STATIC_ROOT = BASE_DIR / 'staticfiles'
   STATIC_URL = '/static/'
   STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
   ```

5. **Collect Static Files**

   ```bash
   python manage.py collectstatic
   ```

6. **Commit and push the changes to GitHub**

   ```bash
   git add .
   git commit -m "Prepare app for deployment"
   git push origin main
   ```
   
   
