#ifndef ANANSIWEBCALC_H
#define ANANSIWEBCALC_H

#include <QMainWindow>

namespace Ui {
    class AnansiWebCalc;
}

class AnansiWebCalc : public QMainWindow
{
    Q_OBJECT

public:
    explicit AnansiWebCalc(QWidget *parent = 0);
    ~AnansiWebCalc();

private:
    Ui::AnansiWebCalc *ui;

private:
    QString str;
    QString strl;
    QString ch;
    QString strResult;
    QString textl;

public:
    float num;
    float numl;
    float ans;

private slots:
    void addi();
    void subs();
    void mult();
    void divi();
    void em();
    void mone();
    void mtwo();
    void mthree();
    void mfour();
    void mfive();
    void msix();
    void mseven();
    void meight();
    void mnine();
    void mzero();
    void mreset();
    void mdot();
    void mpi();
    void mXSq();
};

#endif // ANANSIWEBCALC_H
