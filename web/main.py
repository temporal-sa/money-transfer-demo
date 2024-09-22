from app.index import app

# https://stackoverflow.com/questions/69868760/m1-mac-process-keeps-autogenerating-and-locks-my-port
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8081, debug=True)