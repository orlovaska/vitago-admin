from __future__ import annotations

from PyQt5.QtWidgets import QCheckBox, QLineEdit, QVBoxLayout, QWidget

from app.domain.enums import MimeType
from app.domain.models import Resource
from app.presentation.widgets.common import LabeledField
from app.presentation.widgets.resource_picker import ResourcePicker


class ApplicationForm(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.bundle_id = QLineEdit()
        self.bundle_id.setPlaceholderText("com.example.app")
        self.custom_scheme = QLineEdit()
        self.custom_scheme.setPlaceholderText("audio-guide-spb")
        self.payment_postfix = QLineEdit()
        self.support_chat_url = QLineEdit()
        self.google_play = QCheckBox("Google Play")
        self.app_store = QCheckBox("App Store")
        self.ru_store = QCheckBox("RuStore")
        self.google_play.setChecked(True)
        self.app_store.setChecked(True)
        self.ru_store.setChecked(True)
        self.terms = ResourcePicker()
        self.acc_recovery = ResourcePicker()
        self.gif = ResourcePicker()

        layout = QVBoxLayout(self)
        layout.addWidget(LabeledField("Bundle ID", self.bundle_id, "Например: com.example.app"))
        layout.addWidget(LabeledField("Custom Scheme", self.custom_scheme, "Уникальная схема редиректа после оплаты"))
        layout.addWidget(LabeledField("Постфикс сервиса оплаты", self.payment_postfix))
        layout.addWidget(LabeledField("URL чата поддержки", self.support_chat_url))
        layout.addWidget(self.google_play)
        layout.addWidget(self.app_store)
        layout.addWidget(self.ru_store)
        layout.addWidget(LabeledField("PDF пользовательского соглашения", self.terms))
        layout.addWidget(LabeledField("Заставка при удалении аккаунта", self.acc_recovery))
        layout.addWidget(LabeledField("Начальная анимация (Lottie JSON)", self.gif))

    def set_resources(self, resources: list[Resource]) -> None:
        self.terms.set_resources(resources, MimeType.PDF)
        self.acc_recovery.set_resources(resources, MimeType.PNG)
        self.gif.set_resources(resources, MimeType.JSON)

    def set_support_url(self, url: str) -> None:
        if not self.support_chat_url.text():
            self.support_chat_url.setText(url)

    def errors(self) -> list[str]:
        missing = []
        if not self.bundle_id.text().strip():
            missing.append("Bundle ID")
        if not self.custom_scheme.text().strip():
            missing.append("Custom Scheme")
        if not self.payment_postfix.text().strip():
            missing.append("Постфикс оплаты")
        if not self.support_chat_url.text().strip():
            missing.append("URL чата поддержки")
        return missing

    def to_payload(self) -> dict:
        return {
            "bundle_id": self.bundle_id.text().strip(),
            "customScheme": self.custom_scheme.text().strip(),
            "paymentServicePostfix": self.payment_postfix.text().strip(),
            "supportChatUrl": self.support_chat_url.text().strip(),
            "usePaymentGooglePlay": self.google_play.isChecked(),
            "usePaymentAppStore": self.app_store.isChecked(),
            "usePaymentRuStore": self.ru_store.isChecked(),
            "termsResourceId": self.terms.value(),
            "accRecoveryImageResourceId": self.acc_recovery.value(),
            "gifResourceId": self.gif.value(),
            "isMultiRoute": False,
        }
