from flask import Flask, request, jsonify, render_template, url_for, logging, g, current_app
from flask_cors import CORS
# from flask.views import MethodView
import connexion
import os
from subhub.cfg import CFG
from subhub.subhub_dynamodb import SubHubAccount



def create_app(config=None):
    if CFG('AWS_EXECUTION_ENV', None) is None:
        print(f'offline yes')
        options = {"swagger_ui": True}
        region = 'localhost'
        host = 'http://localhost:8000'
    else:
        options = {"swagger_ui": False}
        region = 'us-west-2'
        host = None
    
    app = connexion.FlaskApp(__name__, specification_dir='./', options=options)
    app.add_api('subhub_api.yaml', pass_context_arg_name='request',
                strict_validation=True)

    if host:
        app.app.subhub_account = SubHubAccount(table_name=CFG.USER_TABLE, region=region, host=host)
    else:
        app.app.subhub_account = SubHubAccount(table_name=CFG.USER_TABLE, region=region)
    if not app.app.subhub_account.model.exists():
        app.app.subhub_account.model.create_table(read_capacity_units=1, write_capacity_units=1, wait=True)

    @app.app.before_request
    def before_request():
        g.subhub_account = current_app.subhub_account
        g.app_system_id = None
    CORS(app.app)
    return app


if __name__ == '__main__':
    print('starting app')
    port = int(os.environ.get("PORT", 5000))
    app = create_app()
    app.debug = True
    app.use_reloader=True
    app.run(host='0.0.0.0', port=port)
