from app.index import app

# https://stackoverflow.com/questions/69868760/m1-mac-process-keeps-autogenerating-and-locks-my-port
if __name__ == '__main__':
    web = app.app_info.get('web', {})
    web_url = web.get('url', {})
    web_ssl = web.get('connection', {}).get('mtls', {})
    print(app.app_info)
    app.run(host=web_url.hostname,
            port=web_url.port,
            debug=True,
            certfile=web_ssl.get('cert_chain_file', None),
            keyfile=web_ssl.get('key_file', None),
            )