import requests
from bs4 import BeautifulSoup
import json
import os
import yfinance as yf
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

def send_mail_report(is_success, error_msg=""):
    gmail_user = os.getenv('MY_GMAIL_USER')
    gmail_pw = os.getenv('MY_GMAIL_PW')
    target_email = "stinlove@kakao.com"

    if not gmail_user or not gmail_pw:
        print("메일 계정 정보가 없습니다. 알림을 건너뜁니다.")
        return

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if not is_success:
        # ❌ 실패했을 때만 메일을 구성하고 발송합니다.
        subject = f"[DAT MONITOR] ⚠️ 업데이트 실패 ({now})"
        body = (
            f"점검이 필요합니다. 쿠키가 만료되었을 가능성이 높습니다.\n\n"
            f"❌ 상세 원인: {error_msg}\n"
            f"⏰ 발생 시간: {now}\n\n"
            f"사장님, 사이트에서 새 쿠키를 추출해 GitHub Secrets를 업데이트 해주세요!"
        )
        
        try:
            msg = MIMEText(body)
            msg['Subject'] = subject
            msg['From'] = gmail_user
            msg['To'] = target_email
            
            with smtplib.SMTP('smtp.gmail.com', 587) as server:
                server.starttls()
                server.login(gmail_user, gmail_pw)
                server.sendmail(gmail_user, target_email, msg.as_string())
            print(f"🚨 업데이트 실패 알림 메일을 발송했습니다. ({now})")
        except Exception as e:
            print(f"메일 발송 에러: {e}")
    else:
        # ✅ 성공 시에는 로그만 남깁니다.
        print(f"✅ 데이터 업데이트 성공 ({now}) - 알림 메일을 발송하지 않습니다.")

def scrape_dat_final():
    url = "https://bitcointreasuries.net/"
    # 사장님, 아래 쿠키는 곧 만료될 수 있으니 나중에 에러나면 다시 업데이트 하셔야 합니다!
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Cookie': '_ga=GA1.1.735990955.1768484196; session=c4e6a4f3-9bae-4368-bb86-cd78f2044956; cf_clearance=MfqJi5nC4zTMmy_ySM_TlepmemDfrGMYd2xXdun8Sxk-1768488123-1.2.1.1-zRB74qLNZgeQmFjt4ovA2rqcqGa_5vBlshf5zmRQBlWeeCLsbA2Vvm0y.B1Asxo2BXlR6JHsbRlp0KqTXfHrvS8IoiTuOI7OqbJsV7tCWLXK3HW5IGbm4A4txlDjvAfOr.c1YZSMqSiz3WmJplo286px856XAmJMtIpnFexNUIitGR4ycHj4nJ8yWpflZKiZasb01gxklTZIGtkBZsrVs0gV5ptFCg9qitkIlkPVZ5Q; _ga_PS4WN3NSZE=GS2.1.s1768487089$o2$g1$t1768488203$j60$l0$h0'
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        all_tables = soup.find_all('table')
        
        base_info = []
        for idx in range(3):
            if idx >= len(all_tables): break
            rows = all_tables[idx].find_all('tr')[1:]
            for row in rows:
                if len(base_info) >= 100: break
                cols = row.find_all(['td', 'th'])
                if len(cols) >= 5:
                    base_info.append({
                        "name": cols[1].get_text(strip=True),
                        "ticker_or_country": cols[3].get_text(strip=True),
                        "btc_holdings": cols[4].get_text(strip=True)
                    })

        extra_info = []
        q_count = 0 
        
        if len(all_tables) >= 4:
            rows_4 = all_tables[3].find_all('tr')[1:]
            for row in rows_4:
                if len(extra_info) >= 100: break
                cols = row.find_all(['td', 'th'])
                if len(cols) >= 7:
                    val1 = cols[5].get_text(strip=True)
                    val2 = cols[6].get_text(strip=True)
                    if '?' in val2:
                        q_count += 1
                    extra_info.append({"extra_val_1": val1, "extra_val_2": val2})

        if len(extra_info) > 10:
            q_ratio = q_count / len(extra_info)
            if q_ratio > 0.8:
                raise Exception(f"EV 데이터 80% 이상({q_count}개)이 물음표로 표시됨. 쿠키 만료 확실.")

        combined_data = []
        for i in range(len(base_info)):
            item = base_info[i]
            if i < len(extra_info): item.update(extra_info[i])
            
            ticker = item["ticker_or_country"]
            if ticker.isalpha() and len(ticker) <= 5:
                try:
                    stock = yf.Ticker(ticker)
                    item["live_price"] = round(stock.fast_info['previous_close'], 2)
                except: item["live_price"] = 0
            else: item["live_price"] = 0
            combined_data.append(item)

        file_path = os.path.join(os.path.dirname(__file__), 'data.json')
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(combined_data, f, ensure_ascii=False, indent=4)
        
        send_mail_report(True)

    except Exception as e:
        send_mail_report(False, str(e))

if __name__ == "__main__":
    scrape_dat_final()
