-- drugs 마스터 데이터 초기 적재
-- 최초 컨테이너 기동 시 1회 자동 실행
\COPY drugs(name, manufacturer) FROM '/docker-entrypoint-initdb.d/02-seed-drugs.csv' CSV HEADER;
