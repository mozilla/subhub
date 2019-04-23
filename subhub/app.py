from flask import Flask, request, jsonify, render_template, url_for, logging
from flask_cors import CORS
# from flask.views import MethodView
import connexion
import os



def create_app(config=None):
    IS_DEPLOYED = os.environ.get("AWS_EXECUTION_ENV")
    if IS_DEPLOYED is None:
        print(f'offline yes')
        options = {"swagger_ui": True}
    else:
        options = {"swagger_ui": False}
    print(f'options {options}')
    app = connexion.FlaskApp(__name__, specification_dir='./', options=options)
    app.add_api('subhub_api.yaml', pass_context_arg_name='request',
                strict_validation=True)

    CORS(app.app)
    return app


if __name__ == '__main__':
    print('starting app')
    port = int(os.environ.get("PORT", 5000))
    app = create_app()
    app.debug = True
    app.run(host='0.0.0.0', port=port)
