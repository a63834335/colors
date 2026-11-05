# -*- coding: utf-8 -*-
from flask import Flask, render_template

app = Flask(__name__)
app.secret_key = 'uchebny-proekt'


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    return render_template('register.html')


@app.route('/palettes')
def palettes():
    return render_template('palettes.html')


if __name__ == '__main__':
    app.run(debug=True)