# -*- coding: utf-8 -*-
# Created: 3/13/2018
# Project : TomatoClock
import datetime
import json
from operator import itemgetter

trans = {
    'TOMATO COLOCK': {'zh_CN': u'番茄时钟', 'en': u'Tomato Clock'},
    "'Minutes Studied'": {'zh_CN': u"'学习分钟数'", 'en': u"'Minutes Studied'"},
    "'Best Focus Hour'": {'zh_CN': u"'最佳学习时段'", 'en': u"'Best Focus Hour'"},
    "'Count of Tomatoes and Minutes'": {'zh_CN': u"'番茄和学习分钟'",
                                        'en': u"'Count of Tomatoes and Minutes'"},
    "'Tomato Count'": {'zh_CN': u"'番茄个数'", 'en': u"'Tomato Count'"},
    "'Productivity'": {'zh_CN': u"'卡片/番茄'", 'en': u"'Cards/Tomato'"},
    "'{a} <br/>{b} Clock: {c} Minutes'": {'zh_CN': u"'{a} <br/>{b} 点: {c} 分钟'",
                                          'en': u"'{a} <br/>{b} Clock: {c} Minutes'"},
}


def _(key):
    from anki.lang import currentLang
    lang = currentLang
    key = key.upper().strip()
    if lang != 'zh_CN' and lang != 'en' and lang != 'fr':
        lang = 'en'  # fallback

    def disp(s):
        return s.lower().capitalize()

    for k, v in trans.items():
        trans[k.upper()] = v

    if key not in trans or lang not in trans[key]:
        return disp(key)
    return trans[key][lang]


class TomatoStats:
    def __init__(self, db, debug=False):
        self.debug = debug
        if self.debug:
            from .db import TomatoDB
            assert isinstance(db, TomatoDB)
        self.db = db
        self._data_by_dates = []

    def reports(self):
        html = """
        %s
        <table width=95%% align=center>
            <tr>
                <td width=300px height=300px id=tomato_cnt align=center></td>
                <td width=300px height=300px id=cards_per_tomato_cnt align=center></td>
            </tr>
            <tr >
                <td width=300px height=300px id=study_minute align=center></td>
                <td width=600px height=300px id=tomato_hour align=center></td>
            </tr>
        </table>
        %s
        """
        return html % (self._js_ref, u"""
        <script>
        {}
        </script>
        """.format(u"".join(
            [
                self._chart_tomato_cnt(),
                self._chart_tomato_hour(),
                self._chart_study_minute(),
                self._chart_cards_per_tomato_cnt()
            ]
        )))

    @property
    def _js_ref(self):
        return u"""
        <script src="http://echarts.baidu.com/examples/vendors/echarts/echarts.min.js"></script>
        """

    def _graph(self, id, conf):
        id = unicode(id, encoding="utf-8")
        html = u"""
        echarts.init(document.getElementById('%(id)s')).setOption(%(conf)s);
        """ % dict(id=id, conf=json.dumps(conf).replace("\"", ""))
        return html

    @property
    def report_days(self):
        return (datetime.datetime.now() + datetime.timedelta(days=-7)).date()

    @property
    def data_by_dates(self):
        if not self._data_by_dates:
            _list_data = self.db.execute(
                """
                select
                  TOMATO_DT,
                  sum(TOMATO_MINS) TT_TOMATO_MINS,
                  sum(TARGET_MINS) TT_TGT_MINS,
                  sum(TOMATO_CNT)  TT_TOMATO_CNT,
                  sum(CARDS_CNT)   TT_CARDS_COUNT
                from (SELECT
                        strftime('%m/%d', ts.tomato_dt)                                                    TOMATO_DT,
                        (strftime('%s', ts.ended) - strftime('%s', ts.started)) / 60.0                     TOMATO_MINS,
                        ts.target_secs / 60.0                                                              TARGET_MINS,
                        (strftime('%s', ts.ended) - strftime('%s', ts.started)) / round(ts.target_secs, 1) TOMATO_CNT,
                        (select count(*)
                         from tomato_session_item tsi
                         where ts.id = tsi.session_id)                                                     CARDS_CNT
                      FROM tomato_session ts
                      WHERE ended IS NOT NULL 
                              AND date(ts.tomato_dt) >= ?
                              AND ts.deck = ?)
                GROUP BY TOMATO_DT
                """, self.report_days, self.db.deck['id']).fetchall()

            if not _list_data:
                self._data_by_dates = [[], [], [], [], []]

            x_dt_labels = ["'%s'" % i[0] for i in _list_data]
            y_tomato_count = [round(i[3], 2) for i in _list_data]
            y_tomato_min = [round(i[2], 2) for i in _list_data]
            y_tomato_target_min = [round(i[1], 2) for i in _list_data]
            y_cards_count = [round(i[4], 2) for i in _list_data]

            self._data_by_dates = [x_dt_labels, y_tomato_count, y_tomato_min, y_tomato_target_min, y_cards_count]
        return self._data_by_dates

    def _chart_study_minute(self, ):
        (x_dt_labels, y_tomato_count,
         y_tomato_min, y_tomato_target_min, y_cards_count
         ) = self.data_by_dates
        if not x_dt_labels:
            return

        conf = dict(
            tooltip=dict(
                trigger="'item'",
            ),
            title={
                "subtext": _("'Minutes Studied'")
            },
            xAxis=dict(data=x_dt_labels),
            yAxis={},
            series=[
                dict(
                    name=_("'Minutes Studied'"),
                    type=u"'bar'",
                    data=y_tomato_min
                )
            ]
        )

        return self._graph("study_minute", conf)

    def _chart_tomato_cnt(self, ):
        (x_dt_labels, y_tomato_count,
         y_tomato_min, y_tomato_target_min, y_cards_count
         ) = self.data_by_dates
        if not x_dt_labels:
            return

        conf = dict(
            tooltip=dict(
                trigger="'item'",
            ),
            title={
                "subtext": _("'Tomato Count'")
            },
            xAxis=dict(data=x_dt_labels),
            yAxis={},
            series=[
                dict(
                    name=_("'Tomato Count'"),
                    type=u"'bar'",
                    data=y_tomato_count
                )
            ]
        )

        return self._graph("tomato_cnt", conf)

    def _chart_cards_per_tomato_cnt(self):
        (x_dt_labels, y_tomato_count,
         y_tomato_min, y_tomato_target_min, y_cards_count
         ) = self.data_by_dates

        if not x_dt_labels:
            return

        y_cards_per_tomato = [round(a / b, 2) for a, b in zip(y_cards_count, y_tomato_count)]

        conf = dict(
            tooltip=dict(
                trigger="'item'",
            ),
            title={
                "subtext": _("'Productivity'")
            },
            xAxis=dict(type="'category'",
                       data=x_dt_labels),
            yAxis=dict(type="'value'"),
            series=[dict(
                name=_("'Productivity'"),
                data=y_cards_per_tomato,
                type="'line'",
                smoth=True), ]
        )

        return self._graph("cards_per_tomato_cnt", conf)

    def _chart_tomato_hour(self, ):
        _list_data = self.db.execute(
            """
            SELECT
              strftime('%H',ts.started)                 HOUR,
             round( sum(ts.target_secs) / 60.0,2) MINS
            FROM tomato_session ts
            WHERE ended IS NOT NULL AND
                  round((strftime('%s', ts.ended) - strftime('%s', ts.started)), 2)
                  >= ts.target_secs
                  AND ts.tomato_dt >= ?
                  AND ts.deck = ?
            GROUP BY strftime('%H',ts.started)
            order by strftime('%H',ts.started)
            """, self.report_days, self.db.deck['id']).fetchall()

        if not _list_data:
            return ''

        if self.debug:
            _list_data = [
                [0, 33.1],
                [1, 22],
                [2, 14],
                [3, 0.5],
                [4, 22.7],
                [5, 19],
                [6, 43],
                [7, 59],
                [8, 20],
                [9, 11],
                [10, 0.9],
                [11, 0.9],
                [12, 0.9],
                [13, 0.9],
                [14, 0.9],
                [25, 0.9],
                [16, 0.9],
                [17, 0.9]
            ]
        _list_data = sorted(_list_data, key=itemgetter(0))
        time_slots = [
            '00:00 - 07:59',
            '08:00 - 10:59',
            '11:00 - 13:59',
            '14:00 - 16:59',
            '17:00 - 21:59',
            '21:00 - 23:59',
        ]
        time_slots_range = [
            (0, 7),
            (8, 11),
            (11, 14),
            (14, 17),
            (17, 21),
            (21, 24),
        ]

        mins_stutied = [0] * time_slots.__len__()
        for i, val in enumerate(_list_data):
            min = val[1]
            for slot_i, time_slot_rng in enumerate(time_slots_range):
                if time_slot_rng[0] <= val[0] < time_slot_rng[1]:
                    mins_stutied[slot_i] = mins_stutied[slot_i] + round(min, 2)

        conf = dict(
            tooltip=dict(
                trigger="'item'",
                formatter=_("'{a} <br/>{b} Clock: {c} Minutes'")
            ),
            title={
                # "text": "'Count of Tomatoes and Minutes'",
                "subtext": _("'Best Focus Hour'")
            },
            xAxis=dict(type="'category'",
                       data=["'%s'" % i for i in time_slots]),
            yAxis=dict(type="'value'"),
            series=[dict(
                name=_("'Best Focus Hour'"),
                data=mins_stutied,
                type="'line'",
                areaStyle={}), ]
        )
        return self._graph("tomato_hour", conf)
