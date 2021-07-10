# v1.0 더 높은 누적수익률로 선택해서 결정하기 (볼린저밴드)
import pandas as pd
import numpy as np
import requests
import pyupbit
import datetime
import time
import os

# my_keys
access_key='RxxAtjdhrudtlr515TCBv4Wc9ycWKILVBsDhE3ZeiJVXadxF'
secret_key='xavsrBGokR53316fqeivyA4ctxFrJgMfjbCCJmxRY5I51048'  # 깃허브 부정 방지 적용됨

# API 접속 함수 (trade api)
def get_candle_1min(tickers, date):
    url = "https://api.upbit.com/v1/candles/minutes/1" # 1분당 금액 가져오기 
    querystring = {"market":tickers,"count":"2", 'to': date}
    response = requests.request("GET", url, params=querystring)
    return response.json()

# 24시간 수익률 표시
def get_candle_1min2(tickers, date):
    url = "https://api.upbit.com/v1/candles/minutes/1" # 1분당 금액 가져오기 
    querystring = {"market":tickers,"count":"24", 'to': date}
    response = requests.request("GET", url, params=querystring)
    return response.json()

# DataFrame(실시간 확보)
def settings(tickers, present_date):
    data=pd.DataFrame(get_candle_1min2(tickers, present_date))
    data=data.sort_values(by='candle_date_time_kst').reset_index(drop=True)
    i=0
    while(i<59): # 데이터 수 확장하기  (2시간 단위)
        try:
            date=data.loc[0,'candle_date_time_kst']
            data2=pd.DataFrame(get_candle_1min2(tickers, date+'+09:00'))
            data=pd.concat([data,data2])  
            data=data.sort_values(by='candle_date_time_kst').reset_index(drop=True)
            i+=1
        except:
            continue
    return data

# 초기 실행함수
def start():
    tickers_list = pyupbit.get_tickers()
    print("")
    print("-----------Upbit Coin Auto control Program------------------------")
    print("|  Version. 1.0 (1 Algorithm)                                    |")
    print("|                                                                |")
    print("|  코인명 작성법: 'KRW-<코인명>'                                 |")
    print("|                                  ex) KRW-EOS  (이오스)         |")
    print("|  참고) 프로그램은 매 1분마다 스스로 작동합니다.                |")
    print("|  참고2) 실행도중 초기화면 이동을 원할 경우 Ctrl+C 입력         |")
    print("|  참고3) 예상수익률은 누적수익률로 계산되었습니다.              |")
    print("|  참고4) 수익률은 과거 24시간 Data를 기반으로 작성되었습니다.   |")
    print("----------------------------------------------made.by Lutto-------\n\n\n")
    Coin=input("Select User Coin: ")
    if Coin in tickers_list:
        print(Coin,'is checked')
        current=datetime.datetime.now()
        print("현재 접속 시간:{0}".format(current.strftime("%Y-%m-%d %H:%M")))
        time.sleep(2)
        return Coin
    else:
        print("잘못된 코인명을 입력했습니다. 코인명을 아래에서 확인 후 원하는 것을 골라 입력해주세요.")
        for name in tickers_list:
            if name.startswith('KRW'):
                print("º"+name, end=", ")
        time.sleep(3)
        os.system("pause")
        os.system("cls")
        start()

# 데이터 확보
def Coin_dataframe(df):
    # 매수, 매도 타이밍 check (RSI 14일 기준)
    
    df['up_open']=0.0 # RSI 구하기 위함
    df['down_open']=0.0

    df['up_vol']=0.0 # VR 구하기 위함
    df['same_vol']=0.0
    df['down_vol']=0.0

    # 전체 데이터 시가 구하기
    for i in range(1,len(df)):
        # 시가 기준(09:00)
        diff=np.round(df.loc[df.index[i],'opening_price']-df.loc[df.index[i-1],'opening_price'],1)
        if diff>0:
            df.loc[df.index[i],'up_open']=diff
            df.loc[df.index[i],'up_vol']=np.round(df.loc[df.index[i],'candle_acc_trade_volume']/1000,1)  # 거래량이 많아 보정해야함
        elif diff<0:
            df.loc[df.index[i],'down_open']=-diff
            df.loc[df.index[i],'down_vol']=np.round(df.loc[df.index[i],'candle_acc_trade_volume']/1000,1)
        elif diff==0.0:
            df.loc[df.index[i],'same_vol']=np.round(df.loc[df.index[i],'candle_acc_trade_volume']/1000,1)
            
    return df

# 볼린저밴드 만들기(upper, middle, lower)
def BAND_data(df, day=20):
    j=0
    temp=df.copy()
    for i in range(day,len(df)+1):   # 종가를 이용
        last_df=df[j:i]
        middle=np.round(last_df['trade_price'].sum()/day,3) # middle 값
        upper=np.round(middle+(np.std(last_df['trade_price'])*2),3) # upper 값
        lower=np.round(middle-(np.std(last_df['trade_price'])*2),3) # lower 값
        temp.loc[i-1,'band_mid']=middle
        temp.loc[i-1,'band_up']=upper
        temp.loc[i-1,'band_low']=lower
        j+=1
    j=0
    for i in range(5,len(df)+1):   # 종가를 이용
        last_df=df[j:i]
        line_5=np.round(last_df['trade_price'].sum()/5,3) # 5 이동평균선 이용
        temp.loc[i-1,'line_5']=line_5
        j+=1
    df=pd.concat([df,temp['band_mid'],temp['band_up'],temp['band_low'], temp['line_5']],axis=1)
    return df

def minute_1(temp_df, i):
    blue_b_price=0
    blue_t_price=0
    blue=0
    red_b_price=0
    red_t_price=0
    red=0
    
    # 일봉 매수, 매도 점 위치 파악 (빨간색, 파란색인지 구별) -> 가격 변수 설정
    chai= np.round(temp_df.loc[temp_df.index[i],'opening_price'],0) - np.round(temp_df.loc[temp_df.index[i],'trade_price'],0)
    if chai >= 0: # 블루봉
        blue_b_price=np.round(temp_df.loc[temp_df.index[i],'trade_price'],0)
        blue_t_price=np.round(temp_df.loc[temp_df.index[i],'opening_price'],0)
        blue=1
    else: #레드봉
        red_b_price=np.round(temp_df.loc[temp_df.index[i],'opening_price'],0)
        red_t_price=np.round(temp_df.loc[temp_df.index[i],'trade_price'],0)   
        red=1
    
    return blue_b_price, blue_t_price, blue, red_b_price, red_t_price, red

# 볼린저 밴드를 이용한 매수 매도 누적 수익률 test 함수
def band_trainig(temp_df, signal, check=False):
    temp_df['B/S']=0  # buy=1, sell=-1
    sign=0  # 매수 or 매도 타이밍
    cnt=0 # 매수 개수
    for i in range(1,len(temp_df)):
        diff=temp_df.loc[temp_df.index[i],'diff']-temp_df.loc[temp_df.index[i-1],'diff']  #차이폭의 매분 변화량은 절대값으로 표현
        mid_price=temp_df.loc[temp_df.index[i],'band_mid']
        upper=temp_df.loc[temp_df.index[i],'band_up']
        lower=temp_df.loc[temp_df.index[i],'band_low']
        line_5=temp_df.loc[temp_df.index[i],'line_5']
        blue=0
        red=0
        
        # 일봉 매수, 매도 점 위치 파악 (빨간색, 파란색인지 구별) -> 가격 변수 설정
        blue_b_price, blue_t_price, blue, red_b_price, red_t_price, red = minute_1(temp_df, i)
            
        # 지지선, 저항선에 걸치면서 폭 변화량 차이가 있는 경우
#         if diff>signal:
#             if blue==1 and (upper<blue_t_price or lower>blue_b_price):   #블루봉 사인
#                 sign=1 # 매수 or 매도 타이밍 발생
#             elif red==1 and (upper<red_t_price or lower>red_b_price):    #레드봉 사인
#                 sign=1 # 매수 or 매도 타이밍 발생
                
#         if sign==1 and diff<signal: # 시그널 지속하며 꺾는점 발생 (진정한 매수, 매도 타이밍)
#             sign=0
#             if blue==1 and blue_t_price<line_5 and mid_price<blue_b_price and cnt>0: # 고점형성 기준 블루봉일시 매도
#                 temp_df.loc[temp_df.index[i],'B/S']=-1   # 매도한다. 
#                 cnt=0

#             elif red==1 and red_t_price<line_5 and mid_price<red_b_price and cnt>0: # 고점형성 기준 레드봉일시 매도
#                 temp_df.loc[temp_df.index[i],'B/S']=-1   # 매도한다. 
#                 cnt=0

#             elif red==1 and mid_price>red_b_price and red_b_price>line_5: # 저점형성 기준 레드봉일시 매수 (레드봉일시만 매수!! (핵심))
#                 temp_df.loc[temp_df.index[i],'B/S']=1   # 매수한다. 
#                 cnt+=1
        if blue==1 and upper<blue_t_price and mid_price<blue_t_price:   #블루봉 사인
            sign=-1 # 매도 타이밍 발생
        elif blue==1 and lower>blue_b_price and mid_price>blue_b_price: 
            sign=1 # 매수 타이밍 발생(1)
        elif red==1 and upper<red_t_price and mid_price<red_t_price:    #레드봉 사인
            sign=-1 # 매도 타이밍 발생(-1)
        elif red==1 and lower>red_b_price and mid_price>red_b_price:
            sign=1 # 매수 타이밍 발생
        
        if sign==-1: # 시그널 지속하며 꺾는점 발생 (진정한 매도 타이밍)
            if blue==1 and blue_t_price<line_5 and mid_price<blue_b_price and cnt>0: # 고점형성 기준 블루봉일시 매도
                temp_df.loc[temp_df.index[i],'B/S']=-1   # 매도한다. 
                cnt=0
                sign=0

            elif red==1 and red_t_price<line_5 and mid_price<red_b_price and cnt>0: # 고점형성 기준 레드봉일시 매도
                temp_df.loc[temp_df.index[i],'B/S']=-1   # 매도한다. 
                cnt=0
                sign=0
                
        elif sign==1: # 시그널 지속하며 꺾는점 발생 (진정한 매수 타이밍)
            if red==1 and mid_price>red_b_price and red_b_price>line_5: # 저점형성 기준 레드봉일시 매수 (레드봉일시만 매수!! (핵심))
                temp_df.loc[temp_df.index[i],'B/S']=1   # 매수한다. 
                cnt+=1
                sign=0
                
        ## 내일 해볼꺼.. 매수를 여러번 하는거 최적의 저점을 찾는 방법은 무엇이 없을까? 지금 이거때문에 수익률 검토가 너무 낮아짐
    return temp_df

#누적수익률 계산 함수
def test_rate(temp_df):
    price=0
    cnt=0 # 처음 개수
    sell_rate=[] # 기간별 수익률
    cnt_sum=[]
    total_rate=1
    for i in range(1,len(temp_df)):
        # 일봉 매수, 매도 점 위치 파악 (빨간색, 파란색인지 구별) -> 가격 변수 설정
        blue_b_price, blue_t_price, blue, red_b_price, red_t_price, red = minute_1(temp_df, i)
        
        if temp_df.loc[i,'B/S']==1 and red==1:   # 매수는 시가로 매수한다. (red일시만 매수)
            price=(price+red_b_price) # red일 시 아랫 부분
            cnt+=1
        elif temp_df.loc[i,'B/S']==-1 and cnt>0  and (blue==1 or red==1):
            if blue==1:  # 블루일시 윗 부분
                sell_p=(blue_t_price*cnt)
            elif red==1: # 레드일시 윗 부분
                sell_p=(red_t_price*cnt)
            rate=np.round(((sell_p-price)/price),4)
            sell_rate.append(rate)
            cnt_sum.append(cnt)
            price=0
            cnt=0
    # 총 누적수익률
    try:
        for rate in sell_rate:
            total_rate*=(1+rate)
        total_rate-=1
        total_rate=np.round(total_rate*100,5)
        if len(cnt_sum)!=0:
            cnt_max=max(cnt_sum)
        else:
            cnt_max=0
    except:
        cnt_max='error'
        total_rate='error'
    return total_rate, cnt_max

def buy_trade(tickers, price, balance_list, day, hour, cnt, buy_cnt): #매수 함수
    try:
        ret=upbit.get_balances()
        check=0
        for name in ret:
            if name['currency']==tickers[4:]:  # 잔고에 있는 매수가 확인
                if float(name['avg_buy_price'])>price:
                    check=0
                else:
                    check=1
        if check==1:
            print('잔고에 있는 평균가 {0}원이 주문가격 {1}원보다 낮아 매수 주문이 취소되었습니다.'.format(name['avg_buy_price'],price))
        else: 
            while len(balance_list) != 0:  # 매수하기 전 미체결된 주문 취소하기
                uuid=balance_list.pop()
                ret=upbit.cancel_order(uuid)
                print('{0} {1} 미체결된 주문이 있어 기존 주문 {2}원이 취소되었습니다.'.format(day,hour,ret['price']))
                cnt-=1
                time.sleep(1)
            ret = upbit.buy_limit_order(tickers, price, buy_cnt) #매수
            balance_list.append(ret['uuid'])
            cnt+=1
            print('{1} {2} 으로 {3}는 {0}원으로 현재 {5}{4}를 매수 주문 완료했습니다.'.format(price,day,hour,tickers,tickers[4:],buy_cnt)) 
        return balance_list, cnt
    except:
        print(ret)
        return balance_list, cnt

def sell_trade(tickers, price, balance_list, day, hour, cnt, buy_cnt): #매도 함수   
    try:
        ret=upbit.get_balances()
        ck=0
        for name in ret:
            if name['currency']==tickers[4:]:  # 잔고에 있는 매수평균가 서칭
                avg_buy_price=float(name['avg_buy_price'])
                ret = upbit.sell_limit_order(tickers, price, buy_cnt*cnt)
                print('{1} {2} 기준으로 {3}는 {0}원으로 매수주문({4}) 만큼 매도 완료했습니다.'.format(price,day,hour,tickers[4:],buy_cnt))
                avg_price=np.round(((price-avg_buy_price)/avg_buy_price*100),2)
                print('매도 주문 체결 시 {0} {1} 수익률은 {2}% 입니다.'.format(day,hour,avg_price))
                balance_list=[]
                ck=1
                cnt=0
        if ck==0:
            print("{0} {1} 코인 조회가 불가능하여 매도 실패하였습니다.".format(day,hour))
            
        return balance_list, cnt
    except:
        print(ret)
        return balance_list, cnt

# 매수 or 매도 프로그램
def trade(tickers, df, balance_list, buy_cnt, sign, cnt, signal): # sign=매수 or 매도 타이밍 # band_trainig 에서 결정된 signal 값
    
    #최신데이터 band 형성
    day=20 # BAND_data에서 day값임
    last_df2=df[len(df)-5:]  # 5일 이평선 참고
    line_5=np.round(last_df2['trade_price'].sum()/5,3)
    last_df=df[len(df)-day:] 
    middle=np.round(last_df['trade_price'].sum()/day,3) # middle 값
    upper=np.round(middle+(np.std(last_df['trade_price'])*2),3) # upper 값
    lower=np.round(middle-(np.std(last_df['trade_price'])*2),3) # lower 값
    df.loc[df.index[-1],'line_5']=line_5
    df.loc[df.index[-1],'band_mid']=middle
    df.loc[df.index[-1],'band_up']=upper
    df.loc[df.index[-1],'band_low']=lower
    df.loc[df.index[-1],'diff']=df.loc[df.index[-1],'band_up']-df.loc[df.index[-1],'band_low']
    df.loc[df.index[-1],'B/S']=0
    blue=0
    red=0
    
    # 일봉 매수, 매도 점 위치 파악 (빨간색, 파란색인지 구별) -> 가격 변수 설정
    blue_b_price, blue_t_price, blue, red_b_price, red_t_price, red = minute_1(df, -1)
    
    #변수 설정
    price=pyupbit.get_current_price(tickers)  #현재 가격
    hour=df.iloc[-1,2][11:16]  #시간
    day=df.iloc[-1,2][0:10]    #날짜
    avg_buy_price=0.0
    avg_price=0.0
    #band에 따른 매수 or 매도 결정
    diff=df.loc[df.index[-1],'diff']-df.loc[df.index[-2],'diff']  #차이폭의 매분 변화량을 표현
    mid_price=df.loc[df.index[-1],'band_mid']
    
    # 지지선, 저항선에 걸치면서 폭 변화량 차이가 있는 경우
#     if diff>signal:
#         if blue==1 and (upper<blue_t_price or lower>blue_b_price):   #블루봉 사인
#             sign=1 # 매수 or 매도 타이밍 발생
#         elif red==1 and (upper<red_t_price or lower>red_b_price):    #레드봉 사인
#             sign=1 # 매수 or 매도 타이밍 발생
            
#     if sign==1 and diff<signal: # 시그널 지속하며 꺾는점 발생 (진정한 매수, 매도 타이밍)
        
#         if blue==1 and blue_t_price<line_5 and mid_price<blue_b_price and cnt>0: # 고점형성 기준 블루봉일시 매도
#             df.loc[df.index[-1],'B/S']=-1   # 매도한다. 
#             balance_list, cnt = sell_trade(tickers, price, balance_list, day, hour, cnt, buy_cnt)
#             sign=0
        
#         elif red==1 and red_t_price<line_5 and mid_price<red_b_price and cnt>0: # 고점형성 기준 레드봉일시 매도
#             df.loc[df.index[-1],'B/S']=-1   # 매도한다. 
#             balance_list, cnt = sell_trade(tickers, price, balance_list, day, hour, cnt, buy_cnt)
#             sign=0
        
#         elif red==1 and mid_price>red_b_price and red_b_price>line_5: # 저점형성 기준 레드봉일시 매수 (레드봉일시만 매수!! (핵심))
#             df.loc[df.index[-1],'B/S']=1   # 매수한다. 
#             balance_list, cnt = buy_trade(tickers, price, balance_list, day, hour, cnt, buy_cnt)
#             sign=0
            
#         else:
#             print('{1} {2} 기준으로 {3}는 {0}원으로 현재 보류중입니다.(singnal 보류 중)'.format(price,day,hour,tickers))
            
    if blue==1 and upper<blue_t_price and mid_price<blue_t_price:   #블루봉 사인
        sign=-1 # 매도 타이밍 발생
    elif blue==1 and lower>blue_b_price and mid_price>blue_b_price: 
        sign=1 # 매수 타이밍 발생(1)
    elif red==1 and upper<red_t_price and mid_price<red_t_price:    #레드봉 사인
        sign=-1 # 매도 타이밍 발생(-1)
    elif red==1 and lower>red_b_price and mid_price>red_b_price:
        sign=1 # 매수 타이밍 발생
    
    if sign==-1 and cnt>0: # 시그널 지속하며 꺾는점 발생 (진정한 매도 타이밍)
        if blue==1 and blue_t_price<line_5 and mid_price<blue_b_price: # 고점형성 기준 블루봉일시 매도
            df.loc[df.index[-1],'B/S']=-1   # 매도한다. 
            balance_list, cnt = sell_trade(tickers, price, balance_list, day, hour, cnt, buy_cnt)
            sign=0

        elif red==1 and red_t_price<line_5 and mid_price<red_b_price: # 고점형성 기준 레드봉일시 매도
            df.loc[df.index[-1],'B/S']=-1   # 매도한다. 
            balance_list, cnt = sell_trade(tickers, price, balance_list, day, hour, cnt, buy_cnt)
            sign=0
            
        else:
            print('{1} {2} 기준으로 {3}는 {0}원으로 현재 보류중입니다.(singnal 보류 중)'.format(price,day,hour,tickers))

    elif sign==1: # 시그널 지속하며 꺾는점 발생 (진정한 매수 타이밍)
        if red==1 and mid_price>red_b_price and red_b_price>line_5: # 저점형성 기준 레드봉일시 매수 (레드봉일시만 매수!! (핵심))
            df.loc[df.index[-1],'B/S']=1   # 매수한다. 
            balance_list, cnt = buy_trade(tickers, price, balance_list, day, hour, cnt, buy_cnt)
            sign=0
            
        else:
            print('{1} {2} 기준으로 {3}는 {0}원으로 현재 보류중입니다.(singnal 보류 중)'.format(price,day,hour,tickers))
    
    else:
        print('{1} {2} 기준으로 {3}는 {0}원으로 현재 보류중입니다.'.format(price,day,hour,tickers))
        
    return balance_list, sign, cnt, df
        
# 반복 함수 설정
def repeat_module(tickers, band_df, start_rate, buy_cnt, signal):
    limit=np.round(signal/2,2)        # 한계 수익률 
    balance_list=[]  # 미체결된 잔고
    sign=0   # band 발생 표시 여부
    cnt=0    # 중복 매수 여부
    while True:
        try:
            time2=datetime.datetime.now()
            if time2.second==1:
                time.sleep(1)
                temp=pd.DataFrame(get_candle_1min(tickers, ''))
                temp.drop([1],axis=0,inplace=True)
                band_df=pd.concat([band_df,temp])
                band_df=band_df.sort_values(by='candle_date_time_kst').reset_index(drop=True)
                balance_list, sign, cnt, band_df=trade(tickers, band_df, balance_list, buy_cnt, sign, cnt, signal)
                rate, cnt_max = test_rate(band_df)
                #print("개발자 전용: test= {0}%".format(rate))
                if rate<0:  # 음수일 경우만 수익률 조정
                    print("-----------------Program Pause------------------------")
                    print("   예상수익률 허용범위 벗어나 시스템 재가동 필요      ")
                    print("                                                      ")
                    print("   현재 매수되어 있는 수량: {0}개".format(cnt))
                    print("-----------------Program Pause------------------------")
                    tickers, band_df, start_rate, buy_cnt, signal=slot_setting(0,tickers)

        except KeyboardInterrupt:   # 무한반복 종료
            print("-------------------------Program Pause-------------------------")
            print("       중복 키 입력으로 시스템 중지 및 초기화면 이동           ")
            print("                                                               ")
            print("       현재 매수되어 있는 수량: {0}개".format(cnt))
            print("-------------------------Program Pause-------------------------")
            os.system("pause")
            os.system("cls")
            tickers, band_df, start_rate, buy_cnt, signal=slot_setting(0,tickers)

# band, signal 최대 수익률 구하기
def max_rate(df):
    max_rate=0
    sel_cnt=0
    sel_df=pd.DataFrame()
    temp_df=BAND_data(df)
    temp_df=temp_df.dropna(0).reset_index(drop=True)
    temp_df['diff']=0.0
    temp_df['diff']=temp_df['band_up']-temp_df['band_low']
    temp_df['diff_diff']=0.0
    for i in range(1,len(temp_df)):  # 차이의 차이를 구함
        temp_df.loc[temp_df.index[i],'diff_diff']=temp_df.loc[temp_df.index[i],'diff']-temp_df.loc[temp_df.index[i-1],'diff']
    signal=temp_df['diff_diff'].quantile(0.10)  # 10프로값 부터 시작
    max_signal=temp_df['diff_diff'].quantile(0.90) #90프로 값까지 시작
    ch_signal=temp_df['diff_diff'].quantile(0.10)
    if np.abs(signal)<=10:
        offer=0.05
    else:
        offer=np.round(np.abs(temp_df['diff_diff'].quantile(0.10)/10),3) # 절대값으로 음수는 없애기
    while signal<max_signal:
        temp_df=band_trainig(temp_df, signal)
        rate, cnt_max=test_rate(temp_df)
        if rate>=max_rate:
            ch_signal=signal
            max_rate=rate
            sel_cnt=cnt_max
            sel_df=temp_df
        #print(" 개발자 전용: signal={0}, {2}, rate={1}".format(signal, rate, ch_signal))
        signal+=offer
    return max_rate, sel_cnt, ch_signal, temp_df

#초기화 함수
def slot_setting(dummy,tickers):
    if dummy==0:   # 예상 수익률의 극심한 변동으로 초기화 세팅 진행할 경우
        tickers =start()
        present_p=pyupbit.get_current_price(tickers)
        limit_order=np.round(5000/present_p,4)
        print("{0} 현재 가격 : {1}원, 최소 주문 요구 코인 수량: {2}개 이상".format(tickers, present_p, limit_order))
    buy_cnt=float(input("한번 매수시 구매할 코인 수량: "))
    print("==================== 초기화 세팅 진행 ====================")
    print("  0. 데이터 생성:   ",end='')
    time2=datetime.datetime.now()
    current_date=time2.strftime("%Y-%m-%dT%H:%M")+':01Z'
    data = settings(tickers, current_date)
    data = Coin_dataframe(data)  # 24시간 사용 예상 수익률
    print(" CLEAR")
    print("  1. 24시간 사용 시 예상 수익률:   ",end='')
    rate, sel_cnt, signal, band_df=max_rate(data)   #24시간 기준 signal 사용
    print(" {0}%".format(rate))
    print("  2. 2시간 사용 시 예상 수익률:   ",end='')
    #band_df.to_csv('test.csv')
    temp_df = band_df[(len(band_df)-120):].reset_index(drop=True)  # 2시간 예상 수익률
    rate2, cnt_max=test_rate(temp_df)
    print(" {0}%".format(rate2))
    print("  3. 2시간 사용 시 중복 매수 최대 횟수:  {0}번".format(cnt_max))
    print("==========================================================")
    time2=datetime.datetime.now()
    print("{0}초 후 프로그램 시작".format(60-time2.second))
    return tickers, band_df, rate, buy_cnt, signal
    
if __name__ == "__main__":
    upbit=pyupbit.Upbit(access_key,secret_key)
    dummy=0 # 0일시 완전 새로 시작
    try:
        tickers, band_df, start_rate, buy_cnt, signal=slot_setting(dummy,'')
        repeat_module(tickers, band_df, start_rate, buy_cnt, signal)
    except:
        print("Program Error")
        os.system("pause")
