import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine

st.set_page_config(page_title="설비별 월별 생산량 분석", layout="wide")
st.title("설비별 월별 생산량 및 세팅 횟수 분석")

uploaded_file = st.file_uploader("파일을 업로드하세요 (CSV 또는 Excel)", type=["csv", "xls", "xlsx"])

@st.cache_data(ttl=3600)
def load_data(uploaded_file):
    if uploaded_file:
        with st.spinner("데이터 로딩 중..."):
            try:
                if uploaded_file.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file)
                else:
                    df = pd.read_excel(uploaded_file, sheet_name=0)
                df['검사일'] = pd.to_datetime(df['검사일'])
                return df
            except Exception as e:
                st.error(f"파일 로딩 중 오류 발생: {e}")
                return None
    else:
        db_connection_str = 'mysql+pymysql://root@192.168.0.30:3306/cardb'
        try:
            with st.spinner("데이터베이스에서 로딩 중..."):
                engine = create_engine(db_connection_str)
                with engine.connect() as db_conn:
                    df = pd.read_sql_query("SELECT * FROM map", db_conn)
                return df
        except Exception as e:
            st.error(f"데이터베이스 연결 오류: {e}")
            return None

df = load_data(uploaded_file)

if df is None or df.empty:
    st.error("데이터가 없습니다.")
    st.stop()

equipment_columns_list = ['건식샌드브러스터', '건식후처리', '경면', '고속호닝기', '단면가공기', '래핑', '바렐', '샌드브러스터', '성형', '수동D/B', '스페셜가공기', '습식브러스터', '시기야', '양두', '용접기', '일관라인(M-GIP)', '자동양두', '자동D/B', '측면브러시', '평면연삭기', '포지일관', '프로파일', 'A102', 'A105', 'A140', 'A907(인폭검사기)', 'AP장비', 'APX101', 'AR', 'C-25(G급용)', 'C-40(스페셜용)', 'C-40(임가공용)', 'C-40(CBN용)', 'C-40(GROOVG용)', 'C-40(MILLG용)', 'C면수동기', 'C면자동기-시론', 'C면자동기-SKC', 'FK200C', 'FLEX', 'FLEX200', 'GIG-21', 'HR', 'KBL', 'SAAKE', 'W/B', 'WAL', 'WB', 'WBR', 'WBT']

equipment_columns = [col for col in equipment_columns_list if col in df.columns]

if not equipment_columns:
    st.error("데이터 파일에 설비 관련 열이 없습니다.")
    st.stop()

# 첫 번째로 등장하는 장비명만 사용
df['설비명'] = df[equipment_columns].apply(lambda row: row.dropna().idxmax() if not row.dropna().empty else None, axis=1)

# '호기' 값을 설비별로 나타내도록 설정 (설비명이 존재하는 값을 기준으로 호기 설정)
def assign_ho(row):
    for col in equipment_columns:
        if pd.notna(row[col]):
            return row[col]
    return '미분류'

df['호기'] = df.apply(assign_ho, axis=1)

# 품명 분리
df['품명_앞자리'] = df['품명'].str[:2]
df['품명_가운데'] = df['품명'].str.extract(r'([0-9]{2})')

# 월별 생산량 및 세팅 횟수 계산
df['월'] = df['검사일'].dt.to_period("M")
monthly_production = df.groupby(['월', '설비명', '호기', '품명_앞자리', '품명_가운데'])['공정투입수'].sum().reset_index()

# 세팅 횟수 계산
monthly_production['세팅 횟수'] = monthly_production.groupby(['설비명', '호기', '월'])[['품명_앞자리', '품명_가운데']].apply(
    lambda x: (x != x.shift()).any(axis=1).cumsum()
).reset_index(level=[0, 1, 2], drop=True)

# Period 객체 문자열 변환
monthly_production['월'] = monthly_production['월'].astype(str)

# 데이터 출력
st.write("### 월별 설비별 생산량 및 세팅 횟수")
st.table(monthly_production)

# 설비 선택 UI
selected_equipment = st.selectbox("설비를 선택하세요", options=monthly_production['설비명'].unique())

# 호기 선택 UI
selected_ho = st.selectbox("호기를 선택하세요", options=monthly_production[monthly_production['설비명'] == selected_equipment]['호기'].unique())

# 필터링된 데이터
filtered_data = monthly_production[(monthly_production['설비명'] == selected_equipment) & (monthly_production['호기'] == selected_ho)]

# 월별 생산량 합계
total_production = filtered_data.groupby('월')['공정투입수'].sum().reset_index()

# 월별 세팅 횟수 합계
total_setting_count = filtered_data.groupby('월')['세팅 횟수'].sum().reset_index()

# 월별 생산량 그래프
fig = px.bar(total_production, x="월", y="공정투입수", title=f"{selected_equipment} ({selected_ho}) 월별 생산량",
             height=500)

# y축 스케일 자동 설정 (값 범위에 맞게)
fig.update_layout(
    yaxis=dict(range=[0, total_production['공정투입수'].max() * 1.2])  # y축의 범위를 생산량에 맞게 설정
)

st.plotly_chart(fig, use_container_width=True)

# 월별 세팅 횟수 그래프
fig2 = px.bar(total_setting_count, x="월", y="세팅 횟수", title=f"{selected_equipment} ({selected_ho}) 월별 세팅 횟수",
              height=500)

# y축 스케일 자동 설정 (값 범위에 맞게)
fig2.update_layout(
    yaxis=dict(range=[0, total_setting_count['세팅 횟수'].max() * 1.2])  # 세팅 횟수에 맞게 y축 범위 조정
)

st.plotly_chart(fig2, use_container_width=True)
