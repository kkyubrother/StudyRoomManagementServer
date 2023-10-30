import os

from flask import Flask, current_app, send_from_directory, make_response, render_template, redirect, request


def create_app() -> Flask:
    app = Flask(__name__, instance_relative_config=True, static_url_path='', static_folder='frontend/web')

    if app.debug:
        app.config.from_object("config.DevelopmentConfig")
        try:
            print("cors")
            from flask_cors import CORS
            CORS(app, resources={"*": {"origins": "*"}})
        except ImportError:
            pass
    else:
        app.config.from_object("config.ProductionConfig")

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    # ensure the log folder exists
    try:
        os.makedirs(app.config["LOG_PATH"])
    except OSError:
        pass

    from . import error_handler
    error_handler.error_handle(app)

    from . import security
    security.init_app(app)

    from . import model
    model.db.init_app(app)
    with app.app_context():
        model.db.create_all()

    from StudyRoomManagementServer.util import sms
    sms.init_app(app=app)

    from StudyRoomManagementServer.util import qr_img
    qr_img.init_app(app)

    from StudyRoomManagementServer.util import receipt
    receipt.init_app(app)

    if app.debug:
        from . import debug
        app.register_blueprint(debug.bp)

    from StudyRoomManagementServer.api import auth
    app.register_blueprint(auth.bp)

    from StudyRoomManagementServer.util import timetable
    timetable.init_app(app)

    from .api import message
    app.register_blueprint(message.bp)

    from . import cms_config
    cms_config.init_app(app)

    from .api import cms_api_config
    app.register_blueprint(cms_api_config.bp)

    from .api import users
    app.register_blueprint(users.bp)
    from .api import books
    app.register_blueprint(books.bp)
    from .api import logs
    app.register_blueprint(logs.bp)
    from .api import rooms
    app.register_blueprint(rooms.bp)
    from .api import departments
    app.register_blueprint(departments.bp)
    from .api import export
    app.register_blueprint(export.bp)
    from .api import pay
    app.register_blueprint(pay.bp)
    from .api import transaction
    app.register_blueprint(transaction.bp)
    from .api import admin
    app.register_blueprint(admin.bp)
    from .api import locker
    app.register_blueprint(locker.bp)
    from .api import coupon
    app.register_blueprint(coupon.bp)
    from .api import commute
    app.register_blueprint(commute.bp)
    from .api import bot
    app.register_blueprint(bot.bp)

    @app.route("/init")
    def init_world():
        from .model import Room, User, db

        for room_data in current_app.config.get("ROOM", []):
            if (
                not Room.query.filter_by(type=room_data["type"])
                .filter_by(no=room_data["no"])
                .first()
            ):
                db.session.add(Room(**room_data))
        db.session.commit()
        return {"message": "okay"}

    @app.route("/api/logout")
    @app.route("/logout")
    def logout():
        resp = make_response(redirect("/"))
        resp.set_cookie("Authorization", "", expires=0)
        return resp

    @app.route("/", defaults={'path': ''})
    def serve(path):
        resp = make_response(send_from_directory(app.static_folder, 'index.html'))
        resp.set_cookie("Authorization", "", expires=0)
        return resp

    @app.route("/qr", defaults={'path': ''})
    def serve_qr(path):
        return render_template("qr.html")

    @app.route("/sound/success")
    def serve_sound_success():
        return make_response(send_from_directory(os.path.join(app.root_path, "static", "sound"), 'qr-success.wav'))

    @app.route("/sound/fail")
    def serve_sound_fail():
        return make_response(send_from_directory(os.path.join(app.root_path, "static", "sound"), 'qr-fail.wav'))

    @app.route("/img/coupon/main.png")
    def serve_image_coupon_main():
        return make_response(send_from_directory(os.path.join(app.root_path, "static", "img"), 'coupon_main.png'))

    @app.route("/js/html5-qrcode")
    def serve_html5_qrcode():
        return make_response(send_from_directory(os.path.join(app.root_path, "static", "js"), 'html5-qrcode.min.js'))

    @app.route("/font/<path:filename>")
    def serve_font(filename):
        return make_response(send_from_directory(os.path.join(app.root_path, "static", "font"), filename))

    from . import __version__

    @app.route("/api/info")
    def get_server_info():
        return {
            "title": __version__.__title__,
            "server_version": __version__.__version__,
            "copyright": __version__.__copyright__,
            "login": bool(request.cookies.get("Authorization"))
        }
    return app
