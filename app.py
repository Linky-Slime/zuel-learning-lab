# -*- coding: utf-8 -*-
"""
    :author: 殷林
    :e-mail: 708883978@qq.com
    :copyright: © 2018 Yin Lin
    :license: MIT, see LICENSE for more details.
"""
import os
import sys

import click
from flask import Flask
from flask import redirect, url_for, render_template, flash, session, Markup,request
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import SubmitField, TextAreaField, StringField, SelectField, PasswordField
from wtforms.validators import DataRequired, Length

from flask_wtf.csrf import CSRFProtect

from datetime import datetime, timedelta

import math


# SQLite URI compatible
WIN = sys.platform.startswith('win')
if WIN:
    prefix = 'sqlite:///'
else:
    prefix = 'sqlite:////'

app = Flask(__name__, template_folder="templates", static_folder="static", static_url_path="/static")
app.jinja_env.trim_blocks = True
app.jinja_env.lstrip_blocks = True

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'secret string')

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', prefix + os.path.join(app.root_path, 'test_db.db'))
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['REGISTER_CODE'] = 'zncjzfdxtsxy'

db = SQLAlchemy(app)

rank_dict = {
    1: 0.3,
    2: 0.24,
    3: 0.21,
    4: 0.205,
    5: 0
}

# handlers
@app.shell_context_processor
def make_shell_context():
    return dict(db=db, User=User, Misson_Data=Misson_Data, Tag=Tag, Card=Card)

@app.cli.command()
@click.option('--drop', is_flag=True, help='Create after drop.')
def initdb(drop):
    """Initialize the database."""
    if drop:
        db.drop_all()
    db.create_all()
    click.echo('Initialized database.')

# 这一句话似乎只用运行一次，
@app.before_first_request
def create_tables():
    db.create_all()




# csrf
csrf=CSRFProtect(app)

# forms
class daily_mission(FlaskForm):
    event_name = StringField('event_name',validators=[DataRequired()])
    event_time = SelectField('event_time',choices=[(1,'做多久?'),(1,'1小时'),(2,'2小时'),(3,'3小时'),
                                                   (4,'4小时'),(5,'5小时'),(6,'6小时')],
                             default=0,validators=[DataRequired()])
    event_fight = StringField('event_fight')
    event_submit = SubmitField('提交')

class Tag_Submit(FlaskForm):
    name = StringField('分组',validators=[DataRequired()])
    event_submit = SubmitField('提交')

class Card_Submit(FlaskForm):
    question = StringField('问题', validators=[DataRequired()])
    answer = TextAreaField('答案', default="优质解答：我不知道")
    rank = SelectField('背诵难度', choices=[(1, '简单'), (2, '正常'),(3, '困难'),
                                             (4, '巨难'), (5, '记了也白记')],
                       default=2, validators=[DataRequired()])
    event_submit = SubmitField('创建卡片')

class login_form(FlaskForm):
    username = StringField('用户名', validators=[DataRequired()])
    password = PasswordField('密码', validators=[DataRequired(), Length(8,64)])
    register_code = StringField('注册码')
    submit = SubmitField('提交')

# database
class User(db.Model):
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, unique=True)
    titlename = db.Column(db.String)
    password = db.Column(db.String)
    expe = db.Column(db.Float, default=0)
    level = db.Column(db.Integer, default=1)
    description = db.Column(db.Text, default='这个人很懒，还没有描述')
    missions = db.relationship('Misson_Data')
    tags = db.relationship('Tag')

class Misson_Data(db.Model):
    mission_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'))
    # 显示的内容
    mission_name = db.Column(db.String(20))
    mission_time = db.Column(db.Integer)
    mission_fight = db.Column(db.String(20))
    # 不显示的内容
    mission_active = db.Column(db.Boolean, default=True) # 判断该任务是否为激活状态，即是否为可签到状态
    mission_stop = db.Column(db.Boolean, default=False) # 判断该任务是否已被删除或更改
    mission_start_time = db.Column(db.DateTime, default=datetime.utcnow) # 任务的开始时间以及完成时间，开始时间需要用于
    log = db.Column(db.String)
    history = db.Column(db.Text)
    sign_time = db.Column(db.DateTime, default=datetime(year=2020,month=1,day=1))

    def __repr__(self):
        return '<任务为 %r>' % self.mission_name

class Card(db.Model):
    card_id = db.Column(db.Integer, primary_key=True)
    card_tag = db.Column(db.Integer, db.ForeignKey('tag.tag_id'))
    # 展示内容
    question = db.Column(db.String)
    answer = db.Column(db.Text)
    memory = db.Column(db.Float(precision="10,4"), default=0)
    # 非展示内容
    score = db.Column(db.Float, index=True)
    rank = db.Column(db.Integer, default=2)
    sign_time = db.Column(db.DateTime)
    log = db.Column(db.String, default='')
    active = db.Column(db.Boolean, default=True)  # 判断该任务是否为激活状态，即是否为可签到状态

class Tag(db.Model):
    tag_id = db.Column(db.Integer, primary_key=True)
    tag_name = db.Column(db.String)
    cards = db.relationship('Card')
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'))

def get_state(string):
    a,b,c,d=(0,0,0,0)
    l = 0
    m = 0
    for i in string:
        if i=='0':
            a += 1
            l = 0
        elif i=='1':
            b += 1
            l += 1
            if l>m: m=l
        elif i=='2':
            c += 1
            l += 1
            if l > m: m = l
        elif i=='3':
            d += 1
            l = 0
    s = a+b+c+d
    return([m,l,a,b,c,d])

@app.route('/', methods=['GET'])
def index():
    test_dat = Misson_Data.query.filter(Misson_Data.mission_stop == False).first()
    print(test_dat)
    return render_template('index.html', dat=test_dat)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = login_form()
    if form.validate_on_submit():
        name = form.username.data
        password = form.password.data
        user = User.query.filter(User.username == name).first()
        if user:
            if user.password==password:
                session['user_id']=user.user_id
                flash(u'登录成功')
                return redirect(url_for('user'))
            else:
                flash('密码错误')
        else:
            flash('不存在的用户')
    return render_template('login.html', dat=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = login_form()
    if form.validate_on_submit():
        if form.register_code.data != app.config['REGISTER_CODE']:
            flash(app.config['REGISTER_CODE'])
        else:
            name = form.username.data
            password = form.password.data
            user = User(username=name, password=password)
            db.session.add(user)
            db.session.commit()
            flash(u'注册成功')
            return redirect(url_for('index'))
    else:
        flash(u'密码需要8位以上')
    return render_template('register.html', dat=form)

@app.route('/user', methods=['GET'])
def user():
    user_id = session.get('user_id')
    info = User.query.filter(User.user_id==user_id).first()
    missions = Misson_Data.query.filter((Misson_Data.mission_stop == False)&(Misson_Data.user_id == user_id)).all()
    dat = []
    for mission in missions:
        log = mission.log
        log2 = get_state(log) # log提供5位输出，分别为最长连续签到了多久,已经连续签到的时间,没签到，完成，完成一半，开摆
        name = mission.mission_name
        stop = mission.mission_stop
        start = mission.mission_start_time.isoformat()[0:10]
        active = mission.mission_active
        start2 = mission.mission_start_time
        dat.append([name]+[active]+[stop]+[start]+log2+[start2]+[log])
    print(dat[0])
    return render_template('user.html', info=info, dat=dat)

@app.route('/schedule', methods=['GET', 'POST'])
def get_schedule():
    if not session.get('user_id'):
        return redirect(url_for('login'))
    user_id = session.get('user_id')
    event_form = daily_mission()
    mission_db = Misson_Data.query.filter((Misson_Data.mission_stop==False) & (Misson_Data.user_id==user_id))
    is_active(mission_db)
    if event_form.validate_on_submit():
        event_name = event_form.event_name.data
        event_time = event_form.event_time.data
        event_fight = event_form.event_fight.data
        if event_fight == '':
            event_fight = '加油！'
        event_dat = Misson_Data(mission_name=event_name, mission_time=event_time, mission_fight=event_fight,
                                mission_active=True, user_id=user_id,
                                sign_time=datetime(year=2025,month=1,day=1), log='', history='')
        db.session.add(event_dat)
        db.session.commit()
        print(request.form)
        return redirect(url_for('get_schedule'))
    return render_template('Schedule.html', dat=mission_db, schedule2=event_form)

@app.route('/change_mission', methods=['POST'])
def edit_note():
    print(request.form)
    dat = request.form
    id = dat.get('id',0)
    note = Misson_Data.query.get(id)
    before_string = str(datetime.utcnow()) + ';' + note.mission_name + ';' + str(
        note.mission_time) + ';' + note.mission_fight
    note.mission_name = dat.get('name', '躺平')
    note.mission_time = dat.get('time', 0)
    note.mission_fight = dat.get('fight', '加油!')
    user_id = note.user_id
    # 记录本次修改
    note.history += before_string
    db.session.commit()
    return redirect(url_for('get_schedule'))

@app.route('/delate_mission', methods=['POST'])
def delate_note():
    print(request.form)
    dat = request.form
    id = dat.get('id',0)
    if id == 0:
        pass # 输出错误
    else:
        note = Misson_Data.query.get(id)
        note.mission_stop = True
        user_id = note.user_id
        db.session.commit()
    return redirect(url_for('get_schedule'))

def is_active(data):
    '''判断任务是否已经签到过了，如果有漏签的，补上0'''
    if hasattr(data, "__iter__"):
        for dat in data:
            start = dat.mission_start_time
            today = datetime.utcnow()
            time1 = datetime(year=start.year, month=start.month, day=start.day)
            time2 = datetime(year=today.year, month=today.month, day=today.day)
            days = (time2 - time1).days+1
            sign_log = dat.log
            # print('active%d' % days, 'log%d' % len(sign_log))
            if len(sign_log)<days:
                dat.mission_active = True
            else:
                dat.mission_active = False
            db.session.commit()
        print('完成更新')
    return('完成更新')

@app.route('/type_mission', methods=['POST'])
def type_note():
    print(request.form)
    dat = request.form
    id = dat.get('id',0)
    type = dat.get('result',0)
    if type == 0:
        pass # 输出错误
    log = Misson_Data.query.get(id)
    user_id = log.user_id
    # 判断是不是连续签到，是的话直接加状态，不是的话就需要补中间的状态
    today = datetime.utcnow()
    time1 = datetime(year=today.year, month=today.month, day=today.day)
    time2 = datetime(year=log.sign_time.year, month=log.sign_time.month, day=log.sign_time.day)
    days = (time1-time2).days
    print('active%d' % days)
    print(log.log)
    '''
    此处days有三种情况，days<0，由于sign_time初始设定为2025年，因此第一次签到必定小于0
    days=0，说明是重复签到(但实际上由于)
    days>1，正常情况，差值是中间漏签的
    '''
    if days<0:
        log.log = log.log + str(type)
        log.sign_time = today
        log.mission_start_time = today
    elif days==0:
        print('重复签到')
    else:
        log.log = log.log + '0'*(days-1) + str(type)
        log.sign_time = today
    db.session.commit()
    return redirect(url_for('get_schedule'))


@app.route('/create_card_meta', methods=['GET'])
def create_card_meta():
    if not session.get('user_id'):
        return redirect(url_for('login'))
    user_id = session.get('user_id')
    tags = Tag.query.filter(Tag.user_id==user_id).first()
    if not tags:
        return redirect(url_for('create_tag'))
    id = tags.tag_id
    return redirect(url_for('create_card', tagid=id))


@app.route('/create_card<int:tagid>', methods=['GET', 'POST'])
def create_card(tagid):
    if not session.get('user_id'):
        return redirect(url_for('login'))
    user_id = session.get('user_id')
    tags = Tag.query.filter(Tag.user_id==user_id).all()
    if not tags:
        return redirect(url_for('create_tag'))
    card_form = Card_Submit()
    if card_form.validate_on_submit():
        question = card_form.question.data
        answer = card_form.answer.data
        rank = card_form.rank.data
        card = Card(question=question, answer=answer, rank=rank, score=0)
        card.card_tag = tagid
        db.session.add(card)
        db.session.commit()
        # 上传
        print(card_form)
        return redirect(url_for('create_card', tagid=tagid))
    return render_template('create_card.html', dat=card_form, tags=tags, tag_id=tagid)

@app.route('/create_tag', methods=['GET', 'POST'])
def create_tag():
    if not session.get('user_id'):
        return redirect(url_for('login'))
    user_id = session.get('user_id')
    tag_form = Tag_Submit()
    if tag_form.validate_on_submit():
        name = tag_form.name.data
        tag = Tag(tag_name=name, user_id=user_id)
        db.session.add(tag)
        db.session.commit()
        # 上传
        return redirect(url_for('create_card', tagid=tag.tag_id))
    return render_template('create_tag.html', dat=tag_form)

@app.route('/memory_meta', methods=['GET'])
def memory_meta():
    if not session.get('user_id'):
        return redirect(url_for('login'))
    user_id = session.get('user_id')
    tags = Tag.query.filter(Tag.user_id==user_id).first() #待修改
    if not tags:
        return redirect(url_for('create_tag'))
    cards = Card.query.filter(Card.card_tag == tags.tag_id).first()
    if not cards:
        return redirect(url_for('create_card', tagid=tags.tag_id))
    id = tags.tag_id
    return redirect(url_for('memory', tagid=id))

def update_cards():
    cards = Card.query.all()
    if hasattr(cards, "__iter__"):
        for card in cards:
            memory = card.memory
            if not card.sign_time:
                card.active = True
                card.score = 0
            else:
                delta = (datetime.utcnow()-card.sign_time).days*24*60+(datetime.utcnow()-card.sign_time).seconds/60
                if card.memory <= 1:
                    if card.score < 1:
                        card.score = (1 - memory) * math.exp(-delta / 1145) + memory * math.exp(-delta / 100000)
                else: card.score = 14
                # 接下来判断今天背了没有，对active进行调整
                today = datetime.utcnow()
                time1 = datetime(year=today.year, month=today.month, day=today.day)
                time2 = datetime(year=card.sign_time.year, month=card.sign_time.month, day=card.sign_time.day)
                days = (time1 - time2).days
                if days <= 0:
                    card.active = False
                    # print('今日已背诵')
                else:
                    card.active = True
                    card.log = card.log + '0' * (days - 1)
        db.session.commit()
        return('完成更新')
    return ('完成更新')

# action 0，1，0表示忘了，不会背，一会再来一次，1表示记住了，并记录active=False,2表示跳过一天，memory减少一点
def update_card(card, action):
    rank = card.rank
    theta = rank_dict.get(rank, 2)
    action = int(action)
    print(action)
    if action==1:
        card.active = False
        card.memory = round(card.memory*0.8+theta, 2)
        card.sign_time = datetime.utcnow()
        card.log += '1'
        card.score = 0
        print('a')
    elif action==0:
        card.score += 1
        card.sign_time = datetime.utcnow()-timedelta(days=1)
    elif action==2:
        card.active = False
        card.memory = round(card.memory*0.9, 2)
        card.sign_time = datetime.utcnow()
        card.log += '2'
        card.score = 0
    db.session.commit()
    return('')

@app.route('/memory<int:tagid>', methods=['GET','POST'])
def memory(tagid):
    if not session.get('user_id'):
        return redirect(url_for('login'))
    user_id = session.get('user_id')
    tags = Tag.query.filter(Tag.user_id==user_id).all()
    # card排序操作
    if not tags:
        return redirect(url_for('create_tag'))
    if (request.method=='GET'):
        card = Card.query.filter(Card.card_tag == tagid).first()
        if not card:
            return redirect(url_for('create_card', tagid=tagid))
        update_cards() #更新所有问题，然后提取
        active_card = Card.query.filter(Card.active==True).first()
        if not active_card:
            flash(u'今日的任务全部完成')
            return redirect(url_for('memorize', tagid=tagid, page=1))
        card = Card.query.filter((Card.card_tag == tagid) & (Card.active == True)).order_by(Card.score).first()
        return render_template('memory.html', card=card, tags=tags, tag_id=tagid)
    elif (request.method=='POST'):
        dat = request.form
        action = dat.get('action', 0)
        card_id = dat.get('card_id', 1)
        card = Card.query.get(card_id)
        update_card(card, action)
        card = Card.query.filter(((Card.active==True) & (Card.card_tag==tagid))).order_by(Card.score).first()
        return render_template('memory.html', card=card, tags=tags, tag_id=tagid)
    else:
        return('出错了')

@app.route('/memorize_meta', methods=['GET'])
def memorize_meta():
    if not session.get('user_id'):
        return redirect(url_for('login'))
    user_id = session.get('user_id')
    tags = Tag.query.filter(Tag.user_id==user_id).first() #待修改
    cards = Card.query.first()
    if not tags:
        return redirect(url_for('create_tag'))
    elif not cards:
        return redirect(url_for('create_card', tagid=tags.tag_id))
    id = tags.tag_id
    return redirect(url_for('memorize', tagid=id, page=1))

@app.route('/memorize<int:tagid>+<int:page>', methods=['GET'])
def memorize(tagid, page):
    if not session.get('user_id'):
        return redirect(url_for('login'))
    user_id = session.get('user_id')
    tags = Tag.query.filter(Tag.user_id==user_id).all()
    cards = Card.query.filter((Card.card_tag==tagid)).order_by(Card.score.desc()).paginate(page=page, per_page=10,
                                                                                           error_out=False)
    return render_template('memorize.html', pagination=cards, cards=cards.items, tags=tags, tag_id=tagid, page=page)


@app.route('/change_card', methods=['POST'])
def edit_card():
    print(request.form)
    dat = request.form
    ida = dat.get('id',0)
    if ida == 0:
        pass # 输出错误
    else:
        note = Card.query.get(ida)
        note.question = dat.get('question', '躺平')
        note.card_tag = dat.get('tag', 1)
        note.rank = dat.get('rank', 2)
        note.answer = dat.get('answer', '优质解答：我不知道')
        # 记录本次修改
        db.session.commit()
    return redirect(url_for('memorize_meta'))

@app.route('/delate_card', methods=['POST'])
def delate_card():
    print(request.form)
    dat = request.form
    ida = dat.get('id',0)
    if ida == 0:
        pass # 输出错误
    else:
        note = Card.query.get(ida)
        db.session.delete(note)
        db.session.commit()
    return redirect(url_for('memorize_meta'))

# 404 error handler
@app.errorhandler(404)
def page_not_found(e):
    return render_template('errors/404.html'), 404


# 500 error handler
@app.errorhandler(500)
def internal_server_error(e):
    return render_template('errors/500.html'), 500


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5001)