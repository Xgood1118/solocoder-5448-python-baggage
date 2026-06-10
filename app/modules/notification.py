from typing import Optional
from datetime import datetime

from app.storage.memory import storage
from app.models.baggage import BaggageStatus

MESSAGES = {
    "zh": {
        BaggageStatus.CHECKED_IN: "您的行李已成功值机，标签号 {tag_id}，航班 {flight}，当前状态：已值机。预计到达时间 {eta}。",
        "security_passed": "您的行李已通过安检，标签号 {tag_id}，当前状态：安检通过。预计到达时间 {eta}。",
        "sorted": "您的行李已完成分拣，标签号 {tag_id}，当前状态：分拣完成。预计到达时间 {eta}。",
        "loaded": "您的行李已装机，标签号 {tag_id}，航班 {flight}，当前状态：已装机。预计到达时间 {eta}。",
        "unloaded": "您的行李已卸机，标签号 {tag_id}，当前状态：已卸机。请前往行李转盘领取。",
        "customs_passed": "您的行李已通过海关，标签号 {tag_id}，当前状态：海关通过。请前往行李转盘领取。",
        "carousel_entered": "您的行李已进入转盘，标签号 {tag_id}，请前往转盘领取。",
        "claimed": "您的行李已被领取，标签号 {tag_id}，感谢您的配合。",
        "departed": "祝您旅途愉快，期待下次再会。",
        "misrouted": "【重要通知】您的行李出现错运，标签号 {tag_id}。我们正在处理，将尽快安排转运至正确目的地。给您带来的不便深表歉意。",
        "damaged": "【通知】您的行李发现损坏，标签号 {tag_id}。请前往行李服务台办理相关手续。",
        "lost": "【紧急通知】您的行李暂时无法追踪，标签号 {tag_id}。我们已启动丢失行李调查流程，如有进展将第一时间通知您。",
        "delayed": "【通知】您的行李延误，标签号 {tag_id}。预计延误 {delay_hours} 小时。我们将为您提供相应补偿。",
    },
    "en": {
        BaggageStatus.CHECKED_IN: "Your baggage has been checked in. Tag: {tag_id}, Flight: {flight}. Status: Checked-in. ETA: {eta}.",
        "security_passed": "Your baggage has passed security. Tag: {tag_id}. Status: Security Passed. ETA: {eta}.",
        "sorted": "Your baggage has been sorted. Tag: {tag_id}. Status: Sorted. ETA: {eta}.",
        "loaded": "Your baggage has been loaded. Tag: {tag_id}, Flight: {flight}. Status: Loaded. ETA: {eta}.",
        "unloaded": "Your baggage has been unloaded. Tag: {tag_id}. Status: Unloaded. Please proceed to baggage claim.",
        "customs_passed": "Your baggage has passed customs. Tag: {tag_id}. Status: Customs Cleared. Please proceed to baggage claim.",
        "carousel_entered": "Your baggage is on the carousel. Tag: {tag_id}. Please collect your baggage.",
        "claimed": "Your baggage has been claimed. Tag: {tag_id}. Thank you.",
        "departed": "We wish you a pleasant journey. See you next time.",
        "misrouted": "[URGENT] Your baggage has been misrouted. Tag: {tag_id}. We are working to reroute it to the correct destination. We apologize for the inconvenience.",
        "damaged": "[Notice] Damage detected on your baggage. Tag: {tag_id}. Please visit the baggage service desk.",
        "lost": "[URGENT] Your baggage is temporarily untraceable. Tag: {tag_id}. We have launched an investigation and will notify you of any updates.",
        "delayed": "[Notice] Your baggage is delayed. Tag: {tag_id}. Estimated delay: {delay_hours} hours. Compensation will be provided accordingly.",
    },
    "ja": {
        BaggageStatus.CHECKED_IN: "お荷物のチェックインが完了しました。タグ番号: {tag_id}、便名: {flight}。ステータス: チェックイン済み。到着予定時刻: {eta}。",
        "security_passed": "お荷物が保安検査を通過しました。タグ番号: {tag_id}。ステータス: 保安検査通過。到着予定時刻: {eta}。",
        "sorted": "お荷物の仕分けが完了しました。タグ番号: {tag_id}。ステータス: 仕分け済み。到着予定時刻: {eta}。",
        "loaded": "お荷物が機内に積み込まれました。タグ番号: {tag_id}、便名: {flight}。ステータス: 積載済み。到着予定時刻: {eta}。",
        "unloaded": "お荷物が機内から降ろされました。タグ番号: {tag_id}。ステータス: 降ろし済み。ターンテーブルへお向かいください。",
        "customs_passed": "お荷物が税関を通過しました。タグ番号: {tag_id}。ステータス: 税関通過。ターンテーブルへお向かいください。",
        "carousel_entered": "お荷物がターンテーブルに到着しました。タグ番号: {tag_id}。お受け取りください。",
        "claimed": "お荷物が引き取られました。タグ番号: {tag_id}。ありがとうございます。",
        "departed": "良いご旅行を。またのお越しをお待ちしております。",
        "misrouted": "【重要】お荷物が誤って別の便に積まれました。タグ番号: {tag_id}。正しい目的地への再送手配を進めております。ご迷惑をおかけして申し訳ございません。",
        "damaged": "【お知らせ】お荷物に破損が見つかりました。タグ番号: {tag_id}。お荷物サービスカウンターへお越しください。",
        "lost": "【緊急】お荷物の追跡が一時的にできなくなっております。タグ番号: {tag_id}。調査を開始しました。進展があり次第ご連絡いたします。",
        "delayed": "【お知らせ】お荷物が遅延しております。タグ番号: {tag_id}。遅延時間: 約 {delay_hours} 時間。所定の補償をご提供いたします。",
    },
    "ko": {
        BaggageStatus.CHECKED_IN: "수하물 체크인이 완료되었습니다. 태그번호: {tag_id}, 항공편: {flight}. 상태: 체크인 완료. 예상도착시간: {eta}.",
        "security_passed": "수하물이 보안검사를 통과했습니다. 태그번호: {tag_id}. 상태: 보안검사 통과. 예상도착시간: {eta}.",
        "sorted": "수하물 분류가 완료되었습니다. 태그번호: {tag_id}. 상태: 분류 완료. 예상도착시간: {eta}.",
        "loaded": "수하물이 항공기에 탑재되었습니다. 태그번호: {tag_id}, 항공편: {flight}. 상태: 탑재 완료. 예상도착시간: {eta}.",
        "unloaded": "수하물이 하역되었습니다. 태그번호: {tag_id}. 상태: 하역 완료. 수하물 찾는 곳으로 이동해 주세요.",
        "customs_passed": "수하물이 세관을 통과했습니다. 태그번호: {tag_id}. 상태: 세관 통과. 수하물 찾는 곳으로 이동해 주세요.",
        "carousel_entered": "수하물이 회전반에 나왔습니다. 태그번호: {tag_id}. 찾아가 주세요.",
        "claimed": "수하물이 수령되었습니다. 태그번호: {tag_id}. 감사합니다.",
        "departed": "즐거운 여행 되세요. 다음에 또 뵙겠습니다.",
        "misrouted": "[긴급] 수하물이 잘못된 항공편에 탑재되었습니다. 태그번호: {tag_id}. 올바른 목적지로 재배송 중입니다. 불편을 끼쳐 죄송합니다.",
        "damaged": "[알림] 수하물에 파손이 발견되었습니다. 태그번호: {tag_id}. 수하물 서비스 데스크를 방문해 주세요.",
        "lost": "[긴급] 수하물 추적이 일시적으로 불가능합니다. 태그번호: {tag_id}. 조사를 시작했으며, 진전이 있으면 즉시 알려드리겠습니다.",
        "delayed": "[알림] 수하물이 지연되었습니다. 태그번호: {tag_id}. 예상 지연시간: {delay_hours} 시간. 적절한 보상을 제공해 드리겠습니다.",
    },
}


def _format_eta(flight) -> str:
    if flight and flight.scheduled_arrival:
        return flight.scheduled_arrival.strftime("%Y-%m-%d %H:%M")
    return "정보 없음"


async def send_status_notification(tag_id: str, status: str):
    baggage = storage.get_baggage(tag_id)
    if not baggage:
        return

    language = baggage.language or "zh"
    messages = MESSAGES.get(language, MESSAGES["zh"])
    template = messages.get(status)

    if not template:
        return

    flight = storage.get_flight(baggage.flight_number)
    eta = _format_eta(flight)

    message = template.format(
        tag_id=baggage.tag_id,
        flight=baggage.flight_number,
        eta=eta,
        delay_hours="N/A",
    )

    notification = {
        "type": "sms",
        "status": status,
        "language": language,
        "message": message,
    }

    storage.add_notification(tag_id, notification)


async def send_anomaly_notification(tag_id: str, anomaly):
    baggage = storage.get_baggage(tag_id)
    if not baggage:
        return

    language = baggage.language or "zh"
    messages = MESSAGES.get(language, MESSAGES["zh"])
    template = messages.get(anomaly.anomaly_type)

    if not template:
        return

    flight = storage.get_flight(baggage.flight_number)
    eta = _format_eta(flight)

    message = template.format(
        tag_id=baggage.tag_id,
        flight=baggage.flight_number,
        eta=eta,
        delay_hours=f"{anomaly.delay_hours:.1f}" if anomaly.delay_hours else "N/A",
    )

    notification = {
        "type": "sms",
        "status": f"anomaly_{anomaly.anomaly_type}",
        "language": language,
        "message": message,
        "anomaly_id": anomaly.anomaly_id,
    }

    storage.add_notification(tag_id, notification)
