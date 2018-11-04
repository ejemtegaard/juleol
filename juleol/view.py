from flask import Flask, Blueprint, render_template, request, session, jsonify, redirect, url_for, flash, g
from flask_bcrypt import Bcrypt
from functools import wraps
from juleol import db
from sqlalchemy import exc
from wtforms import Form, IntegerField, validators, HiddenField, PasswordField, StringField, SelectField
from wtforms.widgets.html5 import NumberInput

bp = Blueprint('view', __name__)
bcrypt = Bcrypt()

class LoginForm(Form):
    year = SelectField("Year", [validators.input_required()], coerce=int)
    name = StringField("Name", [validators.input_required(), validators.Length(1, 255)])
    password = PasswordField("Password", [validators.input_required(), validators.Length(1,255)])

class RatingForm(Form):
    look = IntegerField('Look', [validators.optional(), validators.NumberRange(0, 3)], widget = NumberInput(min=0, max=3))
    smell = IntegerField('Smell', [validators.optional(), validators.NumberRange(0, 3)], widget = NumberInput(min=0, max=3))
    taste = IntegerField('Taste', [validators.optional(), validators.NumberRange(0, 9)], widget = NumberInput(min=0, max=9))
    aftertaste = IntegerField('Aftertaste', [validators.optional(), validators.NumberRange(0, 5)], widget = NumberInput(min=0, max=5))
    xmas = IntegerField('Xmas', [validators.optional(), validators.NumberRange(0, 3)], widget = NumberInput(min=0, max=3))

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not 'user_id' in session:
            return redirect(url_for("view.login"))
        else:
            g.participant = db.Participants.query.filter(db.Participants.id == session['user_id']).first()
            if not g.participant:
                return redirect(url_for("view.login"))
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/', methods=["GET"])
def index():
    tastings = db.Tastings.query.all()
    return render_template('index.html', tastings=tastings)

@bp.route('/login', methods=["GET", "POST"])
def login():
    form = LoginForm(request.form)
    form.year.choices = [(t.year, t.year) for t in db.Tastings.query.all()]
    if request.method == "POST" and form.validate():
        tasting = db.Tastings.query.filter(db.Tastings.year == form.year.data).first()
        if not tasting:
            flash("Invalid year", 'error')
        else:
            participant = db.Participants.query.filter(db.Participants.tasting == tasting).filter(db.Participants.name == form.name.data).first()
            if participant:
                if bcrypt.check_password_hash(participant.password, form.password.data):
                    session['user_id'] = participant.id
                    return redirect(url_for('view.index'))
                else:
                    flash("Invalid user or password", 'error')
            else:
                flash("Invalid user or password", 'error')

    return render_template('login.html', form=form)

@bp.route('/logout', methods=["GET"])
def logout():
    session.pop('user_id', None)
    return redirect(url_for('view.index'))

@bp.route('/result/<int:year>')
def result(year):
    tasting = db.Tastings.query.filter(db.Tastings.year == year).first()
    if not tasting:
        flash("Invalid year", 'error')
        return redirect(url_for('view.index'))

    beer_scores = db.get_beer_scores(tasting)
    participants = db.Participants.query.filter(db.Participants.tasting_id == tasting.id).all()

    return render_template('result.html', beer_scores = beer_scores, tasting = tasting, participants = participants)

@bp.route('/result/<int:year>/<int:participant_id>')
def participant_result(year, participant_id):
    participant = db.Participants.query.join(db.Tastings).filter(db.Participants.id == participant_id).filter(db.Tastings.year == year).one()
    if not participant:
        flash("Invalid participant", 'error')
        return redirect(url_for('view.index'))

    scores = db.participant_scores(participant)
    return render_template('participant_result.html', participant = participant, scores = scores)

@bp.route('/rate/<int:year>', methods=["GET"])
@login_required
def rate(year):
    if not g.participant.tasting.year == year:
        flash("Invalid year for this user", "error")
        return redirect(url_for('view.index'))
    form = RatingForm()
    return render_template('rate.html', form=form)

@bp.route('/rate/<int:year>/<int:beer_number>', methods=["GET", "PUT"])
@login_required
def rate_beer(year, beer_number):
    if not g.participant.tasting.year == year:
        response = jsonify(error = "Invalid year for this user")
        response.status_code = 400
        return response

    beer = db.Beers.query.filter(db.Beers.tasting == g.participant.tasting).filter(db.Beers.number == beer_number).first()
    if not beer:
        response = jsonify(error = "Invalid beer")
        response.status_code = 400
        return response

    if request.method == 'GET':
        taste = db.ScoreTaste.query.filter(db.ScoreTaste.tasting == g.participant.tasting).filter(db.ScoreTaste.beer == beer).first()
        aftertaste = db.ScoreAftertaste.query.filter(db.ScoreAftertaste.tasting == g.participant.tasting).filter(db.ScoreAftertaste.beer == beer).first()
        look = db.ScoreLook.query.filter(db.ScoreLook.tasting == g.participant.tasting).filter(db.ScoreLook.beer == beer).first()
        smell = db.ScoreSmell.query.filter(db.ScoreSmell.tasting == g.participant.tasting).filter(db.ScoreSmell.beer == beer).first()
        xmas = db.ScoreXmas.query.filter(db.ScoreXmas.tasting == g.participant.tasting).filter(db.ScoreXmas.beer == beer).first()

        data = {
                'taste': taste.score,
                'aftertaste': aftertaste.score,
                'look': look.score,
                'smell': smell.score,
                'xmas': xmas.score
                }

        return jsonify(data)

    form = RatingForm(request.form)
    if not form.validate():
        response = jsonify(error = str(form.errors))
        response.status_code = 400
        return response

    try:
        if form.look.data is not None:
            look = db.ScoreLook.query.filter(db.ScoreLook.participant == g.participant).filter(db.ScoreLook.beer == beer).first()
            look.score = form.look.data
            db.db.session.add(look)
        if form.smell.data is not None:
            smell = db.ScoreSmell.query.filter(db.ScoreSmell.participant == g.participant).filter(db.ScoreSmell.beer == beer).first()
            smell.score = form.smell.data
            db.db.session.add(smell)
        if form.taste.data is not None:
            taste = db.ScoreTaste.query.filter(db.ScoreTaste.participant == g.participant).filter(db.ScoreTaste.beer == beer).first()
            taste.score = form.taste.data
            db.db.session.add(taste)
        if form.aftertaste.data is not None:
            aftertaste = db.ScoreAftertaste.query.filter(db.ScoreAftertaste.participant == g.participant).filter(db.ScoreAftertaste.beer == beer).first()
            aftertaste.score = form.aftertaste.data
            db.db.session.add(aftertaste)
        if form.xmas.data is not None:
            xmas = db.ScoreXmas.query.filter(db.ScoreXmas.participant == g.participant).filter(db.ScoreXmas.beer == beer).first()
            xmas.score = form.xmas.data
            db.db.session.add(xmas)
        db.db.session.commit()
    except exc.SQLAlchemyError as e:
        db.db.session.rollback()
        app.logger.error("Error updating scores: {}".format(e))
        response = jsonify(error = "Error updating scores")
        response.status_code = 500
        return response
    
    return jsonify(message="Data updated")