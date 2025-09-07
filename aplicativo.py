@app.route('/')
def painel():
    return render_template('index.html')

@app.route('/bot/sinais')
def sinais():
    return render_template('sinais.html')

@app.route('/bot/automatico')
def automatico():
    return render_template('automatico.html')

@app.route('/bot/cripto')
def cripto():
    return render_template('cripto.html')
