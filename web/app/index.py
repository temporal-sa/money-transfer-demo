from flask import Flask, render_template, g

app = Flask(__name__, template_folder='../templates', static_folder='../static')

app_info = {
    'name': 'Temporal Money Transfer',
    'temporal': {
        'namespace': 'foo'
    }
}
@app.before_request
def apply_app_info():
    g.app_info = app_info

@app.context_processor
def view_app_info():
    return dict(app_info=g.app_info)

@app.route('/layout')
def layout():
    return render_template(template_name_or_list='layout.html')

@app.route('/')
def index():
    return render_template('index.html')
    # return 'Hello Flask, Let\'s do web dev like it\'s 1999!'