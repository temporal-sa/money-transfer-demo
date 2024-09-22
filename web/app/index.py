from flask import Flask, render_template
app = Flask(__name__, template_folder='../templates', static_folder='../static')

@app.route('/layout')
def layout():
    app_info = {
        'name': 'Temporal Money TransferDude',
        'temporal': {
            'namespace': 'foo'
        }
    }
    return render_template(template_name_or_list='layout.html', app_info = app_info)

@app.route('/')
def index():
    return render_template('index.html')
    # return 'Hello Flask, Let\'s do web dev like it\'s 1999!'