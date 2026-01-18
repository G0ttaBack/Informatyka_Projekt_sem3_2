import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QHBoxLayout, QVBoxLayout, QLabel, QSlider)
from PyQt5.QtCore import Qt, QTimer, QPointF
from PyQt5.QtGui import QPainter, QColor, QPen, QPainterPath


class Rura:
    def __init__(self, punkty, grubosc=12, kolor=Qt.gray):
        self.punkty = [QPointF(float(p[0]), float(p[1])) for p in punkty]
        self.grubosc = grubosc
        self.kolor_rury = kolor
        self.kolor_cieczy = QColor(0, 180, 255)
        self.czy_plynie = False

    def ustaw_przeplyw(self, plynie: bool):
        self.czy_plynie = plynie

    #rysowanie rur
    def draw(self, painter: QPainter):
        if len(self.punkty) < 2:
            return

        path = QPainterPath()
        path.moveTo(self.punkty[0])
        for p in self.punkty[1:]:
            path.lineTo(p)

        pen_rura = QPen(self.kolor_rury, self.grubosc, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(pen_rura)
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path)

        #kolorowanie cieczy
        if self.czy_plynie:
            pen_ciecz = QPen(self.kolor_cieczy, max(1, self.grubosc - 4), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(pen_ciecz)
            painter.drawPath(path)

    def point_at_fraction(self, t: float) -> QPointF:
        # Zwraca punkt na rurze w miejscu t=[0..1] długości całkowitej

        # nie ma punktow to zwracamy 0
        if not self.punkty:
            return QPointF(0, 0)

        # Jeden punkt to oznacza ze nie ma rury
        if len(self.punkty) == 1:
            return self.punkty[0]

        #sumowanie dlugosci rury
        seg = []
        total = 0.0
        for i in range(len(self.punkty) - 1):
            a = self.punkty[i]
            b = self.punkty[i + 1]
            d = ((b.x() - a.x()) ** 2 + (b.y() - a.y()) ** 2) ** 0.5
            seg.append(d)
            total += d

        #prawie zerowa, krótka rura to zwracamy poczatkowe punkty
        if total <= 1e-6:
            return self.punkty[0]

        #sciecie t, zeby byly procentem
        t = max(0.0, min(1.0, float(t)))
        dist = t * total
        #znalezienie segmentu na ktorym jest punkt
        for i, d in enumerate(seg):
            if dist <= d:
                a = self.punkty[i]
                b = self.punkty[i + 1]
                if d <= 1e-6:
                    return a
                # interpolacja liniowa punktu na odcinku a->b
                u = dist / d
                return QPointF(a.x() + (b.x() - a.x()) * u, a.y() + (b.y() - a.y()) * u)
            # Jeśli to nie ten segment odejmujemy jego długość i sprawdzamy dalej
            dist -= d
        # Jeśli nie trafiliśmy zwracamy koniec rury
        return self.punkty[-1]

class Zbiornik:
    def __init__(self, x, y, width=100, height=140, nazwa="", pojemnosc=100.0):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.nazwa = nazwa

        self.pojemnosc = float(pojemnosc)
        self.aktualna_ilosc = 0.0
        self.poziom = 0.0

    def dodaj_ciecz(self, ilosc: float) -> float:
        wolne = self.pojemnosc - self.aktualna_ilosc
        dodano = min(float(ilosc), wolne)
        self.aktualna_ilosc += dodano
        self.aktualizuj_poziom()
        return dodano

    def usun_ciecz(self, ilosc: float) -> float:
        usunieto = min(float(ilosc), self.aktualna_ilosc)
        self.aktualna_ilosc -= usunieto
        self.aktualizuj_poziom()
        return usunieto

    def aktualizuj_poziom(self):
        self.poziom = 0.0 if self.pojemnosc <= 0 else (self.aktualna_ilosc / self.pojemnosc)

    def czy_pusty(self) -> bool:
        return self.aktualna_ilosc <= 0.1

    def czy_pelny(self) -> bool:
        return self.aktualna_ilosc >= self.pojemnosc - 0.1

    #punkty zapiecia rur
    def punkt_gora_srodek(self):
        return (self.x + self.width / 2, self.y)

    def punkt_dol_srodek(self):
        return (self.x + self.width / 2, self.y + self.height)

    def punkt_gora_lewo(self):
        return (self.x, self.y)

    def punkt_lewy_bok(self, frac_y: float = 0.5):
        frac_y = max(0.0, min(1.0, float(frac_y)))
        return (self.x, self.y + self.height * frac_y)

    def punkt_prawy_bok(self, frac_y: float = 0.5):
        frac_y = max(0.0, min(1.0, float(frac_y)))
        return (self.x + self.width, self.y + self.height * frac_y)

    def draw(self, painter: QPainter):
        if self.poziom > 0:
            h_cieczy = self.height * self.poziom
            y_start = self.y + self.height - h_cieczy
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(0, 120, 255, 200))
            painter.drawRect(int(self.x + 3), int(y_start), int(self.width - 6), int(max(0, h_cieczy - 2)))

        pen = QPen(Qt.white, 4)
        pen.setJoinStyle(Qt.MiterJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(int(self.x), int(self.y), int(self.width), int(self.height))

        painter.setPen(Qt.white)
        painter.drawText(int(self.x), int(self.y - 10), self.nazwa)

class Pompa:
    def __init__(self, r=18, nazwa="P"):
        self.x = 0.0
        self.y = 0.0
        self.r = r
        self.nazwa = nazwa
        self.on = False
        self.rpm = 40

        self.fault_active = False
        self._fault_timer = QTimer()
        self._fault_timer.setSingleShot(True)
        self._fault_timer.timeout.connect(self._clear_fault)

    def set_pos(self, x: float, y: float):
        self.x = float(x)
        self.y = float(y)

    def is_locked(self) -> bool:
        return self.fault_active

    #jak jest blad
    def trigger_fault(self):
        self.on = False
        self.fault_active = True
        self._fault_timer.start(3000)

    def _clear_fault(self):
        self.fault_active = False

    def draw(self, painter: QPainter):
        painter.setPen(QPen(Qt.white, 3))
        painter.setBrush(QColor(60, 60, 60))
        painter.drawEllipse(int(self.x - self.r), int(self.y - self.r), int(2 * self.r), int(2 * self.r))

        painter.setPen(Qt.NoPen)

        #jesli jest blad to czerwony
        if self.fault_active:
            painter.setBrush(QColor(220, 60, 60, 230))
        else:
            painter.setBrush(QColor(0, 180, 255, 220) if self.on else QColor(120, 120, 120, 120))
        painter.drawEllipse(int(self.x - self.r + 4), int(self.y - self.r + 4), int(2 * (self.r - 4)), int(2 * (self.r - 4)))

        painter.setPen(QPen(Qt.white, 3))
        painter.drawLine(int(self.x - 8), int(self.y), int(self.x + 8), int(self.y))
        painter.drawLine(int(self.x + 8), int(self.y), int(self.x + 2), int(self.y - 6))
        painter.drawLine(int(self.x + 8), int(self.y), int(self.x + 2), int(self.y + 6))


class Zawor:
    def __init__(self, nazwa="V"):
        self.x = 0.0
        self.y = 0.0
        self.w = 34
        self.h = 16
        self.nazwa = nazwa
        self.open = False

    def set_pos(self, x: float, y: float):
        self.x = float(x)
        self.y = float(y)

    def draw(self, painter: QPainter):
        fill = QColor(40, 170, 60, 220) if self.open else QColor(200, 50, 50, 220)
        painter.setPen(QPen(Qt.white, 2))
        painter.setBrush(fill)
        painter.drawRect(int(self.x - self.w/2), int(self.y - self.h/2), int(self.w), int(self.h))

        painter.setPen(QPen(Qt.white, 3))
        if self.open:
            painter.drawLine(int(self.x - 12), int(self.y - 10), int(self.x + 12), int(self.y - 10))
        else:
            painter.drawLine(int(self.x), int(self.y - 18), int(self.x), int(self.y - 2))



class Symulacja(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Symulacja Hydrauliczna")
        self.setFixedSize(1400, 800)
        self.setStyleSheet("background-color:#222;")

        # status na 3 sekundy
        self._status_timer = QTimer()
        self._status_timer.setSingleShot(True)
        self._status_timer.timeout.connect(self._clear_status)
        self.status_text = "OK"

        # zbiorniki
        self.z1 = Zbiornik(50, 90, width=170, height=260, nazwa="Zbiornik 1 (GŁÓWNY)", pojemnosc=300.0)
        self.z1.aktualna_ilosc = 300.0
        self.z1.aktualizuj_poziom()

        self.z2 = Zbiornik(450, 270, nazwa="Zbiornik 2", pojemnosc=100.0)
        self.z3 = Zbiornik(820, 420, nazwa="Zbiornik 3", pojemnosc=100.0)
        self.z4 = Zbiornik(self.z3.x, 110, nazwa="Zbiornik 4", pojemnosc=100.0)

        self.zbiorniki = [self.z1, self.z2, self.z3, self.z4]

        # sterowanie
        self.p12 = Pompa(nazwa="P12")
        self.v12 = Zawor("V12")

        self.p34 = Pompa(nazwa="P34")
        self.v34 = Zawor("V34")

        self.vout = Zawor("VOUT")  # spust z Z4

        self._build_pipes()

        self.timer = QTimer()
        self.timer.timeout.connect(self.tick)
        self.running = False

        self._build_ui()
        self._refresh_manual_lock()
        self._refresh_button_colors()
        self._refresh_status_label()

    def set_status_error(self, msg: str):
        self.status_text = msg
        self._status_timer.start(3000)
        self._refresh_status_label()

    def _clear_status(self):
        self.status_text = "OK"
        self._refresh_status_label()

    def _refresh_status_label(self):
        if self.status_text == "OK":
            self.lbl_status.setText("STATUS: OK")
            self.lbl_status.setStyleSheet("color:#b8ffb8; font-weight:900; padding:6px 10px;")
        else:
            self.lbl_status.setText(f"STATUS: {self.status_text}")
            self.lbl_status.setStyleSheet("color:#ff6666; font-weight:900; padding:6px 10px;")

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(6)
        root.addStretch(1)

        # RZĄD 1
        row1 = QHBoxLayout()
        row1.setSpacing(10)

        self.btn_start = QPushButton("STOP")
        self.btn_start.clicked.connect(self.toggle_sim)
        row1.addWidget(self.btn_start)

        row1.addSpacing(10)

        self.manual_buttons = []
        row1.addLayout(self._manual_box("Z1", self.z1))
        row1.addLayout(self._manual_box("Z2", self.z2))
        row1.addLayout(self._manual_box("Z3", self.z3))
        row1.addLayout(self._manual_box("Z4", self.z4))

        row1.addStretch(1)

        self.lbl_status = QLabel("STATUS: OK")
        self.lbl_status.setFixedWidth(560)
        row1.addWidget(self.lbl_status)

        root.addLayout(row1)

        # RZĄD 2
        row2 = QHBoxLayout()
        row2.setSpacing(12)

        self.btn_v12 = QPushButton("V12")
        self.btn_v12.clicked.connect(self.toggle_v12)
        row2.addWidget(self.btn_v12)

        self.btn_p12 = QPushButton("P12")
        self.btn_p12.clicked.connect(self.toggle_p12)
        row2.addWidget(self.btn_p12)

        self.sld_p12 = QSlider(Qt.Horizontal)
        self.sld_p12.setRange(0, 100)
        self.sld_p12.setValue(self.p12.rpm)
        self.sld_p12.setFixedWidth(150)
        self.sld_p12.valueChanged.connect(lambda v: self._set_rpm(self.p12, v))
        row2.addWidget(self.sld_p12)

        self.btn_v34 = QPushButton("V34")
        self.btn_v34.clicked.connect(self.toggle_v34)
        row2.addWidget(self.btn_v34)

        self.btn_p34 = QPushButton("P34")
        self.btn_p34.clicked.connect(self.toggle_p34)
        row2.addWidget(self.btn_p34)

        self.sld_p34 = QSlider(Qt.Horizontal)
        self.sld_p34.setRange(0, 100)
        self.sld_p34.setValue(self.p34.rpm)
        self.sld_p34.setFixedWidth(150)
        self.sld_p34.valueChanged.connect(lambda v: self._set_rpm(self.p34, v))
        row2.addWidget(self.sld_p34)

        self.btn_vout = QPushButton("VOUT")
        self.btn_vout.clicked.connect(self.toggle_vout)
        row2.addWidget(self.btn_vout)

        row2.addStretch(1)
        root.addLayout(row2)

    def _manual_box(self, name: str, zb: Zbiornik):
        lay = QHBoxLayout()
        lay.setSpacing(6)

        lbl = QLabel(name)
        lbl.setStyleSheet("color:white;font-weight:700;")
        lay.addWidget(lbl)

        b_plus = QPushButton("[+]100%")
        b_plus.setStyleSheet("background:#2d5;color:black;padding:6px 10px;")
        b_plus.clicked.connect(lambda _, z=zb: self.fill(z))
        lay.addWidget(b_plus)

        b_minus = QPushButton("[-]0%")
        b_minus.setStyleSheet("background:#d55;color:white;padding:6px 10px;")
        b_minus.clicked.connect(lambda _, z=zb: self.empty(z))
        lay.addWidget(b_minus)

        self.manual_buttons.extend([b_plus, b_minus])
        return lay

    def _refresh_manual_lock(self):
        for b in self.manual_buttons:
            b.setEnabled(not self.running)

    def _set_rpm(self, pompa: Pompa, v: int):
        pompa.rpm = int(v)
        self.update()

    #funkcja style
    def _btn_style_green(self):
        return "background:#2d5; color:black; padding:6px 10px; font-weight:800;"

    def _btn_style_red(self):
        return "background:#d55; color:white; padding:6px 10px; font-weight:800;"

    def _btn_style_gray(self):
        return "background:#666; color:white; padding:6px 10px; font-weight:800;"

    def _refresh_button_colors(self):
        # Start
        if self.running:
            self.btn_start.setText("RUN")
            self.btn_start.setStyleSheet(self._btn_style_green())
        else:
            self.btn_start.setText("STOP")
            self.btn_start.setStyleSheet(self._btn_style_gray())

        # Zawory
        self.btn_v12.setText("V12: OTW" if self.v12.open else "V12: ZAMK")
        self.btn_v12.setStyleSheet(self._btn_style_green() if self.v12.open else self._btn_style_red())

        self.btn_v34.setText("V34: OTW" if self.v34.open else "V34: ZAMK")
        self.btn_v34.setStyleSheet(self._btn_style_green() if self.v34.open else self._btn_style_red())

        self.btn_vout.setText("VOUT: OTW" if self.vout.open else "VOUT: ZAMK")
        self.btn_vout.setStyleSheet(self._btn_style_green() if self.vout.open else self._btn_style_red())

        # Pompy
        if self.p12.is_locked():
            self.btn_p12.setText("P12: BLAD")
            self.btn_p12.setStyleSheet(self._btn_style_red())
        else:
            self.btn_p12.setText("P12: ON" if self.p12.on else "P12: OFF")
            self.btn_p12.setStyleSheet(self._btn_style_green() if self.p12.on else self._btn_style_gray())

        if self.p34.is_locked():
            self.btn_p34.setText("P34: BLAD")
            self.btn_p34.setStyleSheet(self._btn_style_red())
        else:
            self.btn_p34.setText("P34: ON" if self.p34.on else "P34: OFF")
            self.btn_p34.setStyleSheet(self._btn_style_green() if self.p34.on else self._btn_style_gray())

    def toggle_sim(self):
        self.running = not self.running
        if self.running:
            self.timer.start(20)
        else:
            self.timer.stop()
        self._refresh_manual_lock()
        self._refresh_button_colors()
        self.update()

    def fill(self, zb: Zbiornik):
        if self.running:
            return
        zb.aktualna_ilosc = zb.pojemnosc
        zb.aktualizuj_poziom()
        self.update()

    def empty(self, zb: Zbiornik):
        if self.running:
            return
        zb.aktualna_ilosc = 0.0
        zb.aktualizuj_poziom()
        self.update()

    def toggle_v12(self):
        self.v12.open = not self.v12.open
        self._refresh_button_colors()
        self.update()

    def toggle_p12(self):
        if self.p12.is_locked():
            return
        self.p12.on = not self.p12.on
        self._refresh_button_colors()
        self.update()

    def toggle_v34(self):
        self.v34.open = not self.v34.open
        self._refresh_button_colors()
        self.update()

    def toggle_p34(self):
        if self.p34.is_locked():
            return
        self.p34.on = not self.p34.on
        self._refresh_button_colors()
        self.update()

    def toggle_vout(self):
        self.vout.open = not self.vout.open
        self._refresh_button_colors()
        self.update()

    #budowa rur
    def _build_pipes(self):
        p1 = self.z1.punkt_prawy_bok(0.78)
        p2 = self.z2.punkt_gora_lewo()
        self.r12 = Rura([p1, (p1[0] + 60, p1[1]), (p2[0] - 40, p1[1]), (p2[0] - 40, p2[1]), p2])

        p2s = self.z2.punkt_dol_srodek()
        p3in = self.z3.punkt_lewy_bok(0.82)
        my = max(p2s[1] + 40, p3in[1])
        self.r23 = Rura([p2s, (p2s[0], my), (p3in[0] - 60, my), (p3in[0] - 60, p3in[1]), p3in])

        p3 = self.z3.punkt_gora_srodek()
        p4 = self.z4.punkt_dol_srodek()
        mx = (p3[0] + p4[0]) / 2
        self.r34 = Rura([p3, (mx, p3[1] - 70), (mx, p4[1] + 70), p4])

        p4out = self.z4.punkt_prawy_bok(0.85)
        p4out_end = (p4out[0] + 110, p4out[1])
        self.r_out = Rura([p4out, p4out_end], grubosc=10)

        self.rury = [self.r12, self.r23, self.r34, self.r_out]

        # ikony na rurach z funkcją point at fraction
        self.p12.set_pos(self.r12.point_at_fraction(0.60).x(), self.r12.point_at_fraction(0.60).y())
        self.v12.set_pos(self.r12.point_at_fraction(0.35).x(), self.r12.point_at_fraction(0.35).y())

        self.p34.set_pos(self.r34.point_at_fraction(0.60).x(), self.r34.point_at_fraction(0.60).y())
        self.v34.set_pos(self.r34.point_at_fraction(0.35).x(), self.r34.point_at_fraction(0.35).y())

        pvo = self.r_out.point_at_fraction(0.45)
        self.vout.set_pos(pvo.x(), pvo.y())

    #metoda statyczna nie zmieniajaca w obiekcie
    @staticmethod
    def rpm_to_flow(rpm: int, max_flow: float = 2.0) -> float:
        return (max(0, min(100, rpm)) / 100.0) * max_flow

    def gravity_flow_1_to_2(self) -> float:
        frac = self.z1.aktualna_ilosc / self.z1.pojemnosc
        return 0.15 + 1.15 * frac

    def tick(self):
        # reset animacji
        for r in self.rury:
            r.ustaw_przeplyw(False)
        #wszystkie bledy
        if self.p12.on and self.z2.czy_pelny() and self.z3.czy_pelny():
            self.p12.trigger_fault()
            self.set_status_error("P12 zablokowana: Z2 i Z3 pelne")

        elif self.p12.on and (self.z1.czy_pusty() or (not self.v12.open)):
            self.p12.trigger_fault()
            self.set_status_error("BLAD: P12 (brak wody / V12 zamkniety)")

        if self.p34.on and (self.z3.czy_pusty() or (not self.v34.open)):
            self.p34.trigger_fault()
            self.set_status_error("BLAD: P34 (brak wody / V34 zamkniety)")

        if self.p34.on and self.z4.czy_pelny():
            self.p34.on = False
            self.v34.open = False
            self.set_status_error("Z4 pelny: P34 wylaczona + V34 zamkniety")

        #napelnianie zbiornika
        if (self.z2.aktualna_ilosc > 0.1) and (not self.z3.czy_pelny()):
            flow23 = 0.9  # grawitacja
            if self.p12.on and (not self.p12.is_locked()) and self.v12.open:
                flow23 += self.rpm_to_flow(self.p12.rpm, max_flow=1.6)  # boost "od pompy"
            il = self.z2.usun_ciecz(flow23)
            self.z3.dodaj_ciecz(il)
            self.r23.ustaw_przeplyw(True)

        if self.v12.open and (not self.z1.czy_pusty()) and (not self.z2.czy_pelny()):
            flow12 = self.gravity_flow_1_to_2()
            if self.p12.on and (not self.p12.is_locked()):
                flow12 += self.rpm_to_flow(self.p12.rpm, max_flow=2.2)
            il = self.z1.usun_ciecz(flow12)
            self.z2.dodaj_ciecz(il)
            self.r12.ustaw_przeplyw(True)

        if self.v34.open and self.p34.on and (not self.p34.is_locked()) and (not self.z3.czy_pusty()) and (
        not self.z4.czy_pelny()):
            flow34 = self.rpm_to_flow(self.p34.rpm, max_flow=2.2)
            il = self.z3.usun_ciecz(flow34)
            self.z4.dodaj_ciecz(il)
            self.r34.ustaw_przeplyw(True)

            if self.z4.czy_pelny():
                self.p34.on = False
                self.v34.open = False
                self.set_status_error("Z4 pelny: P34 wylaczona + V34 zamkniety")

        if (not self.p34.on) and self.v34.open and (not self.z4.czy_pusty()) and (not self.z3.czy_pelny()):
            flow43 = 0.7
            il = self.z4.usun_ciecz(flow43)
            self.z3.dodaj_ciecz(il)
            self.r34.ustaw_przeplyw(True)

        if self.vout.open and (not self.z4.czy_pusty()):
            drain = 1.4
            self.z4.usun_ciecz(drain)
            self.r_out.ustaw_przeplyw(True)

        self._refresh_button_colors()
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        for r in self.rury:
            r.draw(p)

        self.v12.draw(p)
        self.p12.draw(p)

        self.v34.draw(p)
        self.p34.draw(p)

        self.vout.draw(p)

        for z in self.zbiorniki:
            z.draw(p)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = Symulacja()
    w.show()
    sys.exit(app.exec_())
