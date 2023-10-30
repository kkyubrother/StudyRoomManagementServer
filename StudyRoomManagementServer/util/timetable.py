import gc
import io
import os
from contextlib import contextmanager
from typing import List

import matplotlib
import matplotlib.figure
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
from flask import Flask

from StudyRoomManagementServer import model
from StudyRoomManagementServer.cms_config import get_config

matplotlib.use('agg')

# rooms: List[str] = []
colors = ['pink', 'lightgreen', 'lightblue', 'wheat', 'salmon']


def figure_to_image(fig: plt.Figure) -> io.BytesIO:
    buf = io.BytesIO()
    fig.savefig(buf, dpi=200)
    buf.seek(0)
    return buf


def _get_room_no(room: model.Room) -> int:
    if room.type == 1:
        room_no = room.no
    elif room.type == 2:
        room_no = 11
    elif room.type == 3:
        room_no = 12
    elif room.type == 4:
        room_no = 13
    else:
        room_no = 14
    return room_no


def _get_color(book: model.RoomBook) -> str:
    if book.status == 100:
        color = "lavender"
    elif book.status == 200 and book.purpose == "event":
        color = "#af7ac5"
    elif book.status == 200 and book.purpose == "seminar":
        color = "#7fb3d5"
    elif book.status == 200 and book.purpose == "meeting":
        color = "#76d7c4"
    elif book.status == 200 and book.purpose == "personal":
        color = "#f7dc6f"
    elif book.status == 200:
        color = "lightblue"
    elif book.status == 300:
        color = "yellow"
    elif book.status == 400:
        color = "salmon"
    else:
        color = "tomato"
    return color


@contextmanager
def figure() -> matplotlib.figure.Figure:
    room_l: List[model.Room] = model.Room.query.all()
    rooms: List[str] = [room.name for room in room_l]
    if get_config().book_room_weekdays_open < get_config().book_room_weekend_open:
        start_time = get_config().book_room_weekdays_open
    else:
        start_time = get_config().book_room_weekend_open

    if get_config().book_room_weekdays_close > get_config().book_room_weekend_close:
        end_time = get_config().book_room_weekdays_close
    else:
        end_time = get_config().book_room_weekend_close

    start_point = (start_time.hour + start_time.minute // 60) - 0.1
    end_point = (end_time.hour + end_time.minute // 60) + 0.1

    fig: matplotlib.figure.Figure = plt.figure(figsize=(16, 8.85), clear=True)

    # Set Axis
    ax = fig.add_subplot(111, alpha=0.5)
    ax.yaxis.grid()
    ax.set_xlim(0.5, len(rooms) + 0.5)
    # ax.set_ylim(23.1, 8.9)
    ax.set_ylim(end_point, start_point)
    ax.set_xticks(range(1, len(rooms) + 1))
    ax.set_xticklabels(rooms)
    ax.set_ylabel('시간')

    # Set Second Axis
    ax2 = ax.twiny().twinx()
    ax2.set_xlim(ax.get_xlim())
    ax2.set_ylim(ax.get_ylim())
    ax2.set_xticks(ax.get_xticks())
    ax2.set_xticklabels(rooms)
    ax2.set_ylabel('시간')

    try:
        yield fig
    finally:
        try:
            fig.clf()
            plt.close(fig)
            plt.close("all")
            plt.clf()
            del fig
            gc.collect()
            # pass
        except:
            pass


def create_timetable(title: str, books: List[model.RoomBook], with_text: bool = True) -> io.BytesIO:
    with figure() as fig:
        for book in books:
            room = model.Room.query.filter_by(id=book.room_id).first()
            room_no = _get_room_no(room) - 0.5  # x 축 정렬
            color = _get_color(book)
            if not (book.status == 200 or book.status == 400):
                continue

            start = book.start_time_second / 60
            end = book.end_time_second / 60

            # plot event
            plt.fill_between(
                [room_no, room_no+0.96],
                [start, start],
                [end, end],
                color=color,
                edgecolor='k',
                linewidth=0.5)

            # plot beginning time
            plt.text(
                x=room_no+0.02,
                y=start+0.05,
                s=f'{int(start)}: {book.start_time_second % 60:0>2}\n - {int(end)}: {book.end_time_second % 60:0>2}',
                va='top',
                fontsize=7)

            if with_text:
                username = model.User.query.filter_by(id=book.user_id).first().username
                department = book.department if book.department is not None else "기타"

                # plot event name
                plt.text(
                    room_no+0.48,
                    (start+end)*0.5,
                    f"[{department:3.3}]\n{username}\n{book.people_no}명 {room.no}",
                    ha='left',
                    va='center', fontsize=9)

        plt.title(title, y=1.07)
        return figure_to_image(fig)


def init_app(app: Flask):
    fm.fontManager.addfont(os.path.join(app.root_path, "static", "font", "NanumGothic.ttf"))
    font = fm.FontProperties(fname=os.path.join(app.root_path, "static", "font", "NanumGothic.ttf"))
    plt.rc('font', family=font.get_name())
