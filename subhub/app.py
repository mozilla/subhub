from flask import Flask, request, jsonify, render_template, url_for
from flask_cors import CORS
# from flask.views import MethodView
import connexion
import os


def create_app(config=None):
    app = connexion.FlaskApp(__name__, specification_dir='')
    app.add_api('subhub_api.yaml')

    CORS(app.app)
    return app


if __name__ == '__main__':
    print('starting app')
    port = int(os.environ.get("PORT", 5000))
    app = create_app()
    app.debug = True
    app.run(host='0.0.0.0', port=port)
