from StudyRoomManagementServer import create_app
# import flask_cors


app = create_app()


if __name__ == "__main__":
    # flask_cors.CORS.init_app(app)
    app.run(host='0.0.0.0')
