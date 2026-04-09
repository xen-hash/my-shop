from app import create_app
from keep_alive import start_keep_alive

application = create_app()
app = application

start_keep_alive(app=app)