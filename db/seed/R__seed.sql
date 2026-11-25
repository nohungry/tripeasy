-- 本檔由 db/seed-build/build_seed.py 產生，請勿手動修改；要改請改腳本後重新產生。
-- 來源：db/seed-build/tripeasy_fakedata.sql、db/seed-build/extra_seed.sql
-- 只在本機與展示環境載入（compose 的 Flyway -locations 加上 db/seed），正式環境不載入。
-- 每個 INSERT 都是 ON CONFLICT DO NOTHING：重跑時既有的資料不會被更新。
-- 改了既有資料列的內容，要 docker compose down -v 重建 DB 才看得到。
-- 主鍵由自然鍵決定；改了主鍵或自然鍵，保留舊 volume 重跑會讓資料重複，要 docker compose down -v。
-- 日期以 seed 載入那天為基準（CURRENT_DATE 在載入時計算一次）；volume 保留太久，行程和優惠券會漸漸過期，要 down -v 重建。

---- 1. 會員基本資料 "user"
INSERT INTO "user" (user_id, name, email, role, password, login_attempts, locked_datetime, avatar_url, preference1, preference2, preference3, login_method, created_at, updated_at) VALUES
('c3d1513b-b8f0-48de-b7c3-3a75485f8ae6', 'Alice Wang', 'alice@example.com', 'User', '$2b$10$9Bd0v0X7eLfhzEL5BC8pROe7OWUfOq4rFDMi.8K/Gg7prMuyn8OKi', 0, NULL, 'http://localhost:3000/uploads/seed/avatar.svg', 1, 2, 3, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('c35f34c3-337f-410b-b57a-e439a7ba969b', 'Bob Chen', 'bob@example.com', 'admin', '$2b$10$9Bd0v0X7eLfhzEL5BC8pROe7OWUfOq4rFDMi.8K/Gg7prMuyn8OKi', 1, NULL, 'http://localhost:3000/uploads/seed/avatar.svg', 2, 1, 3, 2, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('568ed618-7b23-4b88-a2fb-d519d1176a63', 'Carol Lin', 'carol@example.com', 'User', '$2b$10$9Bd0v0X7eLfhzEL5BC8pROe7OWUfOq4rFDMi.8K/Gg7prMuyn8OKi', NULL, NULL, NULL, 3, 2, 1, 3, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
ON CONFLICT DO NOTHING;

---- 2. 會員第三方登入資料 "socialLogin"
INSERT INTO "socialLogin" (login_id, user_id, provider_method, provider_id, provider_token, created_at, updated_at) VALUES
('750acc52-29d1-4d0a-8f70-0c91995f3c76', 'c3d1513b-b8f0-48de-b7c3-3a75485f8ae6', 'google', 'google_1234567890', 'ya29.a0AfH6SMAExampleGoogleToken', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('997a8370-5d3f-4f02-a4f5-d957e64ba5f5', 'c35f34c3-337f-410b-b57a-e439a7ba969b', 'facebook', 'facebook_9876543210', 'EAAGm0PX4ZCpsBADExampleFacebookToken', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('a923181b-86c3-4862-be63-76f53c6e0d40', '568ed618-7b23-4b88-a2fb-d519d1176a63', 'apple', 'apple_1122334455', 'd6bbf92f9c3eExampleAppleToken', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
ON CONFLICT DO NOTHING;

---- 3. 會員等級資料 "user_level"
INSERT INTO "user_level" (level_id, user_id, level, name, badge_url, travel_point, benefits, created_at, updated_at) VALUES
('f4bae213-bb36-481f-9cef-8d991dbd8761', 'c3d1513b-b8f0-48de-b7c3-3a75485f8ae6', 'Level 3', 'Explorer', 'http://localhost:3000/uploads/seed/badge.svg', 1500, 'Free airport lounge access; 10% discount on tours', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('e6480f7d-1571-45ef-a9f2-952d75e07d4d', 'c35f34c3-337f-410b-b57a-e439a7ba969b', 'Level 5', 'Adventure Master', 'http://localhost:3000/uploads/seed/badge.svg', 3000, 'VIP travel concierge; Free travel insurance', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('ba5c7244-2adc-4240-8167-8c446056c193', '568ed618-7b23-4b88-a2fb-d519d1176a63', 'Level 2', 'Rookie Traveler', 'http://localhost:3000/uploads/seed/badge.svg', 800, 'Priority customer support; Welcome gift', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
ON CONFLICT DO NOTHING;

---- 4. 優惠卷資料 "coupon"
INSERT INTO "coupon" (coupon_id, code, discount, description, expire_date, created_at, updated_at) VALUES
('9905bf64-566c-4bd6-952c-e7a12a73ffef', 'WEL100', 100.0, '首次註冊禮，折抵新台幣 100 元', (TIMESTAMP '2025-12-31 23:59:59' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('b6f79db8-1516-4d3a-9141-29dd256835e2', 'SUM050', 50.0, '夏日旅遊季，折抵新台幣 50 元', (TIMESTAMP '2025-08-31 23:59:59' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('dffebeb5-1a73-426f-8c3d-9b2a8f74108f', 'TRV010', 10.0, '旅遊商品折抵新台幣 10 元', (TIMESTAMP '2025-09-30 23:59:59' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('7ab87d9e-8ff0-42ad-8252-939d1d80e21b', 'VIP300', 300.0, '尊榮會員專屬，折抵新台幣 300 元', (TIMESTAMP '2025-12-31 23:59:59' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('e875ca7f-a393-4d6c-bb44-07d53bfd8255', 'SPR020', 20.0, '春季限定，旅遊折抵新台幣 20 元', (TIMESTAMP '2025-05-31 23:59:59' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
ON CONFLICT DO NOTHING;

---- 5. 旅遊項目資料 "tour"
INSERT INTO "tour" (tour_id, type, item, status, title, slogan, tour_start_date, tour_end_date, days, price, country, region, address, google_map_url, calendar_url, preference1, preference2, preference3, notice, description, cover_image, img1, img1_desc, img2, img2_desc, img3, img3_desc, img4, img4_desc, img5, img5_desc, img6, img6_desc, created_at, updated_at) VALUES
('c35e011b-ffe4-48ea-8511-9f27ef0d5d69', 'tourgroup', 'travel', 1, '北海道雪景 5 日深度遊', '穿越銀白世界，體驗最美冬季', (TIMESTAMP '2025-12-01 00:00:00' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), (TIMESTAMP '2025-12-05 23:59:59' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), 5, 45000, 'Japan', 'Hokkaido', '札幌市中央區南1條西2丁目', 'https://goo.gl/maps/hokkaido1', 'https://calendar.google.com/event?hokkaido1', 1, 2, 3, '請攜帶防寒衣物。', '探索北海道最美雪景與溫泉之旅。', 'http://localhost:3000/uploads/seed/tour.svg', 'http://localhost:3000/uploads/seed/tour.svg', '札幌夜景', 'http://localhost:3000/uploads/seed/tour.svg', '小樽運河', 'http://localhost:3000/uploads/seed/tour.svg', '登別溫泉', 'http://localhost:3000/uploads/seed/tour.svg', '旭川動物園', 'http://localhost:3000/uploads/seed/tour.svg', '富良野薰衣草', 'http://localhost:3000/uploads/seed/tour.svg', '冰雪祭典', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('9fd27d62-39ba-4b57-8015-6cfc47bb0a52', 'tourgroup', 'travel', 1, '馬爾地夫蜜月天堂 6 日', '享受專屬你的藍色海洋假期', (TIMESTAMP '2025-11-10 00:00:00' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), (TIMESTAMP '2025-11-15 23:59:59' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), 6, 98000, 'Maldives', 'Male', '北馬列環礁私人島嶼', 'https://goo.gl/maps/maldives1', 'https://calendar.google.com/event?maldives1', 2, 1, 3, '請攜帶防曬用品。', '入住水上別墅，專屬浪漫行程。', 'http://localhost:3000/uploads/seed/tour.svg', 'http://localhost:3000/uploads/seed/tour.svg', '水上別墅景色', 'http://localhost:3000/uploads/seed/tour.svg', '海上活動', 'http://localhost:3000/uploads/seed/tour.svg', '私人沙灘', 'http://localhost:3000/uploads/seed/tour.svg', '環礁浮潛', 'http://localhost:3000/uploads/seed/tour.svg', 'SPA中心', 'http://localhost:3000/uploads/seed/tour.svg', '夕陽巡航', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('85f6fdfb-7a95-4379-8fd3-568b0810b46e', 'backpacker', 'food', 1, '大阪美食自由行', '胃袋的無限探險', null, null, 0, 15000, 'Japan', 'Osaka', '道頓堀美食街', 'https://goo.gl/maps/osaka1', 'https://calendar.google.com/event?osaka1', 3, 1, 2, '請注意行程中包含生食餐點。', '深入大阪尋找道地美食與居酒屋。', 'http://localhost:3000/uploads/seed/tour.svg', 'http://localhost:3000/uploads/seed/tour.svg', '章魚燒', 'http://localhost:3000/uploads/seed/tour.svg', '燒肉體驗', 'http://localhost:3000/uploads/seed/tour.svg', '居酒屋文化', 'http://localhost:3000/uploads/seed/tour.svg', '大阪壽司', 'http://localhost:3000/uploads/seed/tour.svg', '道頓堀夜景', 'http://localhost:3000/uploads/seed/tour.svg', '黑門市場', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('57bfb290-092a-40c7-a68c-7b1a032cfe64', 'backpacker', 'spot', 1, '巴黎歷史建築巡禮', '在歷史的街道中穿梭', null, null, 0, 22000, 'France', 'Paris', '巴黎拉丁區', 'https://goo.gl/maps/paris2', 'https://calendar.google.com/event?paris2', 1, 3, 2, '穿著舒適的步行鞋。', '漫步歷史古蹟與文學街區。', 'http://localhost:3000/uploads/seed/tour.svg', 'http://localhost:3000/uploads/seed/tour.svg', '巴黎聖母院', 'http://localhost:3000/uploads/seed/tour.svg', '盧森堡公園', 'http://localhost:3000/uploads/seed/tour.svg', '羅丹美術館', 'http://localhost:3000/uploads/seed/tour.svg', '先賢祠', 'http://localhost:3000/uploads/seed/tour.svg', '拉丁區書店', 'http://localhost:3000/uploads/seed/tour.svg', '塞納河畔', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('1692beb1-be37-4a73-93e4-89d0adf1250c', 'backpacker', 'hotel', 1, '曼谷設計旅店探索', '感受泰式設計美學', null, null, 0, 9000, 'Thailand', 'Bangkok', '曼谷素坤逸路', 'https://goo.gl/maps/bangkok1', 'https://calendar.google.com/event?bangkok1', 2, 1, 3, '入住時間依飯店規定。', '選擇最具設計感的平價住宿。', 'http://localhost:3000/uploads/seed/tour.svg', 'http://localhost:3000/uploads/seed/tour.svg', '曼谷設計旅館', 'http://localhost:3000/uploads/seed/tour.svg', '夜市巡禮', 'http://localhost:3000/uploads/seed/tour.svg', '昭披耶河景', 'http://localhost:3000/uploads/seed/tour.svg', '大皇宮一日遊', 'http://localhost:3000/uploads/seed/tour.svg', '文青咖啡店', 'http://localhost:3000/uploads/seed/tour.svg', '市集探險', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('8c74c63e-933e-4623-aa4c-f3814db9c6c2', 'tourgroup', 'travel', 1, '義大利深度文化之旅', '在藝術與美食中迷失', (TIMESTAMP '2025-10-15 00:00:00' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), (TIMESTAMP '2025-10-22 23:59:59' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), 8, 72000, 'Italy', 'Rome', '羅馬市中心西班牙廣場', 'https://goo.gl/maps/rome1', 'https://calendar.google.com/event?rome1', 1, 2, 3, '行程部分需攀爬古蹟階梯。', '穿越千年歷史，體驗義式浪漫。', 'http://localhost:3000/uploads/seed/tour.svg', 'http://localhost:3000/uploads/seed/tour.svg', '羅馬競技場', 'http://localhost:3000/uploads/seed/tour.svg', '聖彼得大教堂', 'http://localhost:3000/uploads/seed/tour.svg', '特雷維噴泉', 'http://localhost:3000/uploads/seed/tour.svg', '西班牙階梯', 'http://localhost:3000/uploads/seed/tour.svg', '梵蒂岡博物館', 'http://localhost:3000/uploads/seed/tour.svg', '羅馬廣場', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('6045e5a7-50f4-4cfc-814a-bface065157f', 'backpacker', 'spot', 1, '首爾咖啡文青小旅行', '在咖啡香裡漫遊城市', null, null, 0, 9500, 'Korea', 'Seoul', '弘大入口站周邊', 'https://goo.gl/maps/seoul1', 'https://calendar.google.com/event?seoul1', 3, 1, 2, '注意部分巷弄無電梯設施。', '探訪首爾最具文藝氣息的街區與咖啡店。', 'http://localhost:3000/uploads/seed/tour.svg', 'http://localhost:3000/uploads/seed/tour.svg', '延南洞文青街', 'http://localhost:3000/uploads/seed/tour.svg', '首爾森林', 'http://localhost:3000/uploads/seed/tour.svg', '聖水洞咖啡店', 'http://localhost:3000/uploads/seed/tour.svg', '弘大藝術牆', 'http://localhost:3000/uploads/seed/tour.svg', '城東區手作市集', 'http://localhost:3000/uploads/seed/tour.svg', '夜市甜品巡禮', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('9486ac9a-ab9d-4282-a6db-03fb0ccc84c7', 'backpacker', 'hotel', 2, '清邁自然旅宿體驗', '在綠意環繞中放鬆身心', null, null, 0, 7800, 'Thailand', 'Chiang Mai', '古城區瓦洛洛市場附近', 'https://goo.gl/maps/chiangmai1', 'https://calendar.google.com/event?chiangmai1', 2, 3, 1, '民宿僅提供基本設施，無電梯。', '在清邁體驗傳統泰北文化與自然風光。', 'http://localhost:3000/uploads/seed/tour.svg', 'http://localhost:3000/uploads/seed/tour.svg', '清邁古城', 'http://localhost:3000/uploads/seed/tour.svg', '素貼山夜景', 'http://localhost:3000/uploads/seed/tour.svg', '瓦洛洛市場', 'http://localhost:3000/uploads/seed/tour.svg', '寧曼路商圈', 'http://localhost:3000/uploads/seed/tour.svg', '周六市集', 'http://localhost:3000/uploads/seed/tour.svg', '寺廟文化探索', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('b6e2735c-db96-4497-a197-e56c52e2aa64', 'backpacker', 'food', 1, '高雄夜市美食攻略', '不容錯過的小吃巡禮', null, null, 0, 4200, 'Taiwan', 'Kaohsiung', '六合夜市', 'https://goo.gl/maps/kaohsiung1', 'https://calendar.google.com/event?kaohsiung1', 1, 2, 3, '請自備零錢及環保餐具。', '從六合夜市吃到瑞豐夜市，探訪高雄最強美食。', 'http://localhost:3000/uploads/seed/tour.svg', 'http://localhost:3000/uploads/seed/tour.svg', '六合夜市美食', 'http://localhost:3000/uploads/seed/tour.svg', '瑞豐夜市人氣小吃', 'http://localhost:3000/uploads/seed/tour.svg', '旗津海鮮街', 'http://localhost:3000/uploads/seed/tour.svg', '新崛江甜品', 'http://localhost:3000/uploads/seed/tour.svg', '鹽埕區老店', 'http://localhost:3000/uploads/seed/tour.svg', '高雄港夜景', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('f7cdc48d-7443-4b5b-b12a-31a5fa287dd2', 'tourgroup', 'travel', 1, '紐西蘭壯麗景觀自駕遊', '開啟最自由的冒險', (TIMESTAMP '2025-11-05 00:00:00' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), (TIMESTAMP '2025-11-15 23:59:59' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), 11, 85000, 'New Zealand', 'South Island', '基督城市中心', 'https://goo.gl/maps/nz1', 'https://calendar.google.com/event?nz1', 3, 1, 2, '請攜帶國際駕照並確保駕駛經驗。', '從冰河到峽灣，體驗純粹自然。', 'http://localhost:3000/uploads/seed/tour.svg', 'http://localhost:3000/uploads/seed/tour.svg', '庫克山冰川', 'http://localhost:3000/uploads/seed/tour.svg', '皇后鎮湖光山色', 'http://localhost:3000/uploads/seed/tour.svg', '米佛峽灣巡航', 'http://localhost:3000/uploads/seed/tour.svg', '蒂卡波湖星空', 'http://localhost:3000/uploads/seed/tour.svg', '箭鎮金礦小鎮', 'http://localhost:3000/uploads/seed/tour.svg', '瓦納卡湖', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('dfe1a4a5-f228-4ac2-820b-fd8e96b7fd33', 'tourgroup', 'travel', 1, '冰島極光 8 日探索', '追逐綠色光幕的極地冒險', (TIMESTAMP '2025-12-26 00:00:00' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), (TIMESTAMP '2026-01-02 23:59:59' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), 8, 120000, 'Iceland', 'Reykjavik', '雷克雅維克港區', 'https://goo.gl/maps/extra1', 'https://calendar.google.com/event?extra1', 4, 5, 1, '請攜帶保暖衣物與防滑鞋。', '環島追極光、藍湖溫泉與冰河健行。', 'http://localhost:3000/uploads/seed/tour.svg', 'http://localhost:3000/uploads/seed/tour.svg', 'Reykjavik景點1', 'http://localhost:3000/uploads/seed/tour.svg', 'Reykjavik景點2', 'http://localhost:3000/uploads/seed/tour.svg', 'Reykjavik景點3', 'http://localhost:3000/uploads/seed/tour.svg', 'Reykjavik景點4', 'http://localhost:3000/uploads/seed/tour.svg', 'Reykjavik景點5', 'http://localhost:3000/uploads/seed/tour.svg', 'Reykjavik景點6', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('c2e03b7d-b117-4bea-94d6-59e753b00d90', 'tourgroup', 'travel', 1, '瑞士鐵道山岳 7 日', '搭乘景觀列車穿越阿爾卑斯', (TIMESTAMP '2025-08-28 00:00:00' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), (TIMESTAMP '2025-09-03 23:59:59' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), 7, 110000, 'Switzerland', 'Zurich', '蘇黎世中央車站', 'https://goo.gl/maps/extra2', 'https://calendar.google.com/event?extra2', 2, 6, 4, '高山行程請注意高度適應。', '冰河列車、少女峰與策馬特小鎮。', 'http://localhost:3000/uploads/seed/tour.svg', 'http://localhost:3000/uploads/seed/tour.svg', 'Zurich景點1', 'http://localhost:3000/uploads/seed/tour.svg', 'Zurich景點2', 'http://localhost:3000/uploads/seed/tour.svg', 'Zurich景點3', 'http://localhost:3000/uploads/seed/tour.svg', 'Zurich景點4', 'http://localhost:3000/uploads/seed/tour.svg', 'Zurich景點5', 'http://localhost:3000/uploads/seed/tour.svg', 'Zurich景點6', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('9d2e5cdc-230a-4a0a-a7d5-4eb00039fed0', 'tourgroup', 'travel', 1, '西班牙陽光巡禮 9 日', '熱情陽光下的建築與美食', (TIMESTAMP '2025-07-19 00:00:00' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), (TIMESTAMP '2025-07-27 23:59:59' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), 9, 90000, 'Spain', 'Madrid', '馬德里太陽門廣場', 'https://goo.gl/maps/extra3', 'https://calendar.google.com/event?extra3', 3, 1, 7, '夏季氣溫高，請做好防曬。', '高第建築、佛朗明哥與海鮮燉飯。', 'http://localhost:3000/uploads/seed/tour.svg', 'http://localhost:3000/uploads/seed/tour.svg', 'Madrid景點1', 'http://localhost:3000/uploads/seed/tour.svg', 'Madrid景點2', 'http://localhost:3000/uploads/seed/tour.svg', 'Madrid景點3', 'http://localhost:3000/uploads/seed/tour.svg', 'Madrid景點4', 'http://localhost:3000/uploads/seed/tour.svg', 'Madrid景點5', 'http://localhost:3000/uploads/seed/tour.svg', 'Madrid景點6', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('7d6b03fa-e9bb-497d-8962-975ae377ca50', 'backpacker', 'food', 1, '台南小吃巡禮', '一口一口吃遍府城', NULL, NULL, 0, 3000, 'Taiwan', 'Tainan', '台南中西區國華街', 'https://goo.gl/maps/extra4', 'https://calendar.google.com/event?extra4', 1, 3, 2, '部分店家週一公休。', '從牛肉湯到碗粿，走訪在地老店。', 'http://localhost:3000/uploads/seed/tour.svg', 'http://localhost:3000/uploads/seed/tour.svg', 'Tainan景點1', 'http://localhost:3000/uploads/seed/tour.svg', 'Tainan景點2', 'http://localhost:3000/uploads/seed/tour.svg', 'Tainan景點3', 'http://localhost:3000/uploads/seed/tour.svg', 'Tainan景點4', 'http://localhost:3000/uploads/seed/tour.svg', 'Tainan景點5', 'http://localhost:3000/uploads/seed/tour.svg', 'Tainan景點6', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('4cf0efbd-2f6f-4586-9bbf-e2aea735fe74', 'backpacker', 'food', 1, '東京拉麵地圖', '一碗一碗找出本命拉麵', NULL, NULL, 0, 4500, 'Japan', 'Tokyo', '東京新宿區', 'https://goo.gl/maps/extra5', 'https://calendar.google.com/event?extra5', 3, 2, 1, '熱門店家需排隊。', '豚骨、醬油、沾麵的人氣名店路線。', 'http://localhost:3000/uploads/seed/tour.svg', 'http://localhost:3000/uploads/seed/tour.svg', 'Tokyo景點1', 'http://localhost:3000/uploads/seed/tour.svg', 'Tokyo景點2', 'http://localhost:3000/uploads/seed/tour.svg', 'Tokyo景點3', 'http://localhost:3000/uploads/seed/tour.svg', 'Tokyo景點4', 'http://localhost:3000/uploads/seed/tour.svg', 'Tokyo景點5', 'http://localhost:3000/uploads/seed/tour.svg', 'Tokyo景點6', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('474a2d5e-8dda-40fa-83bf-a80f646b33eb', 'backpacker', 'food', 1, '曼谷街頭美食', '夜市與路邊攤的泰式滋味', NULL, NULL, 0, 3800, 'Thailand', 'Bangkok', '曼谷耀華力路', 'https://goo.gl/maps/extra6', 'https://calendar.google.com/event?extra6', 2, 3, 1, '請注意食物辣度。', '船麵、芒果糯米飯與炭烤海鮮。', 'http://localhost:3000/uploads/seed/tour.svg', 'http://localhost:3000/uploads/seed/tour.svg', 'Bangkok景點1', 'http://localhost:3000/uploads/seed/tour.svg', 'Bangkok景點2', 'http://localhost:3000/uploads/seed/tour.svg', 'Bangkok景點3', 'http://localhost:3000/uploads/seed/tour.svg', 'Bangkok景點4', 'http://localhost:3000/uploads/seed/tour.svg', 'Bangkok景點5', 'http://localhost:3000/uploads/seed/tour.svg', 'Bangkok景點6', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('6b7ee8db-b242-4e34-8c22-33c111662feb', 'backpacker', 'spot', 1, '京都古寺散步', '在千年古都慢慢走', NULL, NULL, 0, 6000, 'Japan', 'Kyoto', '京都東山區', 'https://goo.gl/maps/extra7', 'https://calendar.google.com/event?extra7', 5, 2, 3, '寺院內請保持安靜。', '清水寺、伏見稻荷與嵐山竹林。', 'http://localhost:3000/uploads/seed/tour.svg', 'http://localhost:3000/uploads/seed/tour.svg', 'Kyoto景點1', 'http://localhost:3000/uploads/seed/tour.svg', 'Kyoto景點2', 'http://localhost:3000/uploads/seed/tour.svg', 'Kyoto景點3', 'http://localhost:3000/uploads/seed/tour.svg', 'Kyoto景點4', 'http://localhost:3000/uploads/seed/tour.svg', 'Kyoto景點5', 'http://localhost:3000/uploads/seed/tour.svg', 'Kyoto景點6', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('fb300345-ba38-48f2-be6e-b16c4380d642', 'backpacker', 'spot', 1, '倫敦博物館漫遊', '免費博物館裡的大英收藏', NULL, NULL, 0, 7500, 'UK', 'London', '倫敦布盧姆斯伯里', 'https://goo.gl/maps/extra8', 'https://calendar.google.com/event?extra8', 4, 5, 2, '部分展館需預約時段。', '大英博物館、自然史博物館與泰特現代館。', 'http://localhost:3000/uploads/seed/tour.svg', 'http://localhost:3000/uploads/seed/tour.svg', 'London景點1', 'http://localhost:3000/uploads/seed/tour.svg', 'London景點2', 'http://localhost:3000/uploads/seed/tour.svg', 'London景點3', 'http://localhost:3000/uploads/seed/tour.svg', 'London景點4', 'http://localhost:3000/uploads/seed/tour.svg', 'London景點5', 'http://localhost:3000/uploads/seed/tour.svg', 'London景點6', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('6fc80f12-46ab-4e4c-b6b2-47056d7d0403', 'backpacker', 'spot', 1, '新加坡花園城市導覽', '鋼骨叢林裡的綠色奇蹟', NULL, NULL, 0, 6800, 'Singapore', 'Singapore', '新加坡濱海灣', 'https://goo.gl/maps/extra9', 'https://calendar.google.com/event?extra9', 6, 4, 2, '戶外行程請準備雨具。', '濱海灣花園、植物園與小印度街區。', 'http://localhost:3000/uploads/seed/tour.svg', 'http://localhost:3000/uploads/seed/tour.svg', 'Singapore景點1', 'http://localhost:3000/uploads/seed/tour.svg', 'Singapore景點2', 'http://localhost:3000/uploads/seed/tour.svg', 'Singapore景點3', 'http://localhost:3000/uploads/seed/tour.svg', 'Singapore景點4', 'http://localhost:3000/uploads/seed/tour.svg', 'Singapore景點5', 'http://localhost:3000/uploads/seed/tour.svg', 'Singapore景點6', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('144d34ec-2c8c-491f-9f7c-def1351e49d6', 'backpacker', 'hotel', 1, '沖繩海景度假旅店', '推開窗就是蔚藍海岸', NULL, NULL, 0, 8800, 'Japan', 'Okinawa', '那霸市美榮橋', 'https://goo.gl/maps/extra10', 'https://calendar.google.com/event?extra10', 1, 4, 2, '入住時間下午三點起。', '全海景客房，步行即可到海灘。', 'http://localhost:3000/uploads/seed/tour.svg', 'http://localhost:3000/uploads/seed/tour.svg', 'Okinawa景點1', 'http://localhost:3000/uploads/seed/tour.svg', 'Okinawa景點2', 'http://localhost:3000/uploads/seed/tour.svg', 'Okinawa景點3', 'http://localhost:3000/uploads/seed/tour.svg', 'Okinawa景點4', 'http://localhost:3000/uploads/seed/tour.svg', 'Okinawa景點5', 'http://localhost:3000/uploads/seed/tour.svg', 'Okinawa景點6', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('581c88ef-479d-4aea-9330-d83ed9c2ba71', 'backpacker', 'hotel', 1, '峇里島別墅旅宿', '私人泳池的熱帶度假', NULL, NULL, 0, 12000, 'Indonesia', 'Bali', '烏布稻田區', 'https://goo.gl/maps/extra11', 'https://calendar.google.com/event?extra11', 2, 4, 6, '別墅內禁止明火。', '獨棟別墅附泳池，含每日早餐。', 'http://localhost:3000/uploads/seed/tour.svg', 'http://localhost:3000/uploads/seed/tour.svg', 'Bali景點1', 'http://localhost:3000/uploads/seed/tour.svg', 'Bali景點2', 'http://localhost:3000/uploads/seed/tour.svg', 'Bali景點3', 'http://localhost:3000/uploads/seed/tour.svg', 'Bali景點4', 'http://localhost:3000/uploads/seed/tour.svg', 'Bali景點5', 'http://localhost:3000/uploads/seed/tour.svg', 'Bali景點6', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('ed54e664-c3e4-4d1d-a937-091b65b2085f', 'backpacker', 'hotel', 1, '河內古城精品旅店', '住進老城區的法式小樓', NULL, NULL, 0, 6500, 'Vietnam', 'Hanoi', '河內還劍區', 'https://goo.gl/maps/extra12', 'https://calendar.google.com/event?extra12', 3, 5, 1, '老城區夜間較為吵雜。', '步行可達水上木偶劇院與夜市。', 'http://localhost:3000/uploads/seed/tour.svg', 'http://localhost:3000/uploads/seed/tour.svg', 'Hanoi景點1', 'http://localhost:3000/uploads/seed/tour.svg', 'Hanoi景點2', 'http://localhost:3000/uploads/seed/tour.svg', 'Hanoi景點3', 'http://localhost:3000/uploads/seed/tour.svg', 'Hanoi景點4', 'http://localhost:3000/uploads/seed/tour.svg', 'Hanoi景點5', 'http://localhost:3000/uploads/seed/tour.svg', 'Hanoi景點6', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('d67415c9-fd5e-4d84-8a11-7afab5d84ba3', 'backpacker', 'hotel', 1, '釜山海岸旅店', '聽著海浪入睡的港都旅宿', NULL, NULL, 0, 7200, 'Korea', 'Busan', '釜山海雲台', 'https://goo.gl/maps/extra13', 'https://calendar.google.com/event?extra13', 1, 2, 5, '海景房數量有限。', '海雲台海灘旁，附設早餐咖啡廳。', 'http://localhost:3000/uploads/seed/tour.svg', 'http://localhost:3000/uploads/seed/tour.svg', 'Busan景點1', 'http://localhost:3000/uploads/seed/tour.svg', 'Busan景點2', 'http://localhost:3000/uploads/seed/tour.svg', 'Busan景點3', 'http://localhost:3000/uploads/seed/tour.svg', 'Busan景點4', 'http://localhost:3000/uploads/seed/tour.svg', 'Busan景點5', 'http://localhost:3000/uploads/seed/tour.svg', 'Busan景點6', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
ON CONFLICT DO NOTHING;

---- 6. 旅遊產品細項資料 "tour_detail"
INSERT INTO "tour_detail" (tour_detail_id, tour_id, feature_img1, feature_desc1, feature_img2, feature_desc2, feature_img3, feature_desc3, itinerary, created_at, updated_at) VALUES
('a3cc4fdb-414e-4208-a53b-6120ae2592f9', 'c35e011b-ffe4-48ea-8511-9f27ef0d5d69', 'http://localhost:3000/uploads/seed/feature.svg', '旭川雪祭典體驗', 'http://localhost:3000/uploads/seed/feature.svg', '美瑛白金青池探訪', 'http://localhost:3000/uploads/seed/feature.svg', '登別地獄谷探險', 'Day1: 札幌市區巡禮,Day2: 小樽運河,Day3: 美瑛青池,Day4: 登別溫泉,Day5: 旭川雪祭', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('c00905f3-da8e-472d-9246-6acc45fd6499', '9fd27d62-39ba-4b57-8015-6cfc47bb0a52', 'http://localhost:3000/uploads/seed/feature.svg', '水上別墅享受', 'http://localhost:3000/uploads/seed/feature.svg', '私人島嶼浮潛', 'http://localhost:3000/uploads/seed/feature.svg', '夕陽巡航浪漫', 'Day1: 抵達馬列,Day2: 私人島浮潛,Day3: SPA與日光浴,Day4: 水上別墅活動,Day5: 浪漫晚宴,Day6: 自由活動', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('51e3b359-714c-43d5-8aff-dc87a6f8fdaa', '8c74c63e-933e-4623-aa4c-f3814db9c6c2', 'http://localhost:3000/uploads/seed/feature.svg', '羅馬競技場探訪', 'http://localhost:3000/uploads/seed/feature.svg', '托斯卡尼鄉村漫遊', 'http://localhost:3000/uploads/seed/feature.svg', '梵蒂岡藝術之旅', 'Day1: 羅馬市區巡禮,Day2: 梵蒂岡博物館,Day3: 羅馬古城,Day4: 托斯卡尼自由行,Day5: 比薩斜塔,Day6: 佛羅倫斯藝術街區,Day7: 羅馬購物日,Day8: 返回', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('421f2d41-49b0-4742-a256-fb3eb2898045', 'f7cdc48d-7443-4b5b-b12a-31a5fa287dd2', 'http://localhost:3000/uploads/seed/feature.svg', '庫克山冰河健行', 'http://localhost:3000/uploads/seed/feature.svg', '蒂卡波星空夜拍', 'http://localhost:3000/uploads/seed/feature.svg', '米佛峽灣巡航體驗', 'Day1: 基督城市區探索,Day2: 蒂卡波湖星空,Day3: 庫克山健行,Day4: 皇后鎮自由行,Day5: 米佛峽灣巡航,Day6: 弗朗茲約瑟夫冰河健行,Day7-11: 南島深度自由探索', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('2646e6cb-f38b-4960-9f53-082fc7b035dc', '57bfb290-092a-40c7-a68c-7b1a032cfe64', 'http://localhost:3000/uploads/seed/feature.svg', '巴黎聖母院巡禮', 'http://localhost:3000/uploads/seed/feature.svg', '塞納河畔夜遊', 'http://localhost:3000/uploads/seed/feature.svg', '拉丁區藝術巷弄', 'Day1: 巴黎聖母院參觀,Day2: 塞納河遊船,Day3: 拉丁區文學之旅', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('0ee28113-c5b4-404d-abfb-331e71e19036', '6045e5a7-50f4-4cfc-814a-bface065157f', 'http://localhost:3000/uploads/seed/feature.svg', '延南洞文青街探訪', 'http://localhost:3000/uploads/seed/feature.svg', '聖水洞咖啡巡禮', 'http://localhost:3000/uploads/seed/feature.svg', '弘大街頭藝術欣賞', 'Day1: 延南洞文青咖啡館巡禮,Day2: 聖水洞手作街探險,Day3: 弘大夜市與藝術街探索', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('e25808ae-1ded-4f9a-9aef-9d8f37e00ddd', 'dfe1a4a5-f228-4ac2-820b-fd8e96b7fd33', 'http://localhost:3000/uploads/seed/feature.svg', 'Reykjavik特色一', 'http://localhost:3000/uploads/seed/feature.svg', 'Reykjavik特色二', 'http://localhost:3000/uploads/seed/feature.svg', 'Reykjavik特色三', 'Day1: Reykjavik行程1,Day2: Reykjavik行程2,Day3: Reykjavik行程3,Day4: Reykjavik行程4,Day5: Reykjavik行程5,Day6: Reykjavik行程6,Day7: Reykjavik行程7,Day8: Reykjavik行程8', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('9a69bf6b-6d97-4a83-8eaa-625bebdc4da0', 'c2e03b7d-b117-4bea-94d6-59e753b00d90', 'http://localhost:3000/uploads/seed/feature.svg', 'Zurich特色一', 'http://localhost:3000/uploads/seed/feature.svg', 'Zurich特色二', 'http://localhost:3000/uploads/seed/feature.svg', 'Zurich特色三', 'Day1: Zurich行程1,Day2: Zurich行程2,Day3: Zurich行程3,Day4: Zurich行程4,Day5: Zurich行程5,Day6: Zurich行程6,Day7: Zurich行程7', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('31458927-630a-4e52-8f5f-bc19fc174274', '9d2e5cdc-230a-4a0a-a7d5-4eb00039fed0', 'http://localhost:3000/uploads/seed/feature.svg', 'Madrid特色一', 'http://localhost:3000/uploads/seed/feature.svg', 'Madrid特色二', 'http://localhost:3000/uploads/seed/feature.svg', 'Madrid特色三', 'Day1: Madrid行程1,Day2: Madrid行程2,Day3: Madrid行程3,Day4: Madrid行程4,Day5: Madrid行程5,Day6: Madrid行程6,Day7: Madrid行程7,Day8: Madrid行程8,Day9: Madrid行程9', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('970f5f82-c7e6-4a37-b215-27f8eb43adb8', '7d6b03fa-e9bb-497d-8962-975ae377ca50', 'http://localhost:3000/uploads/seed/feature.svg', 'Tainan特色一', 'http://localhost:3000/uploads/seed/feature.svg', 'Tainan特色二', 'http://localhost:3000/uploads/seed/feature.svg', 'Tainan特色三', 'Day1: Tainan行程1,Day2: Tainan行程2,Day3: Tainan行程3', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('63473c01-8e6c-472b-8285-b984641fa4c9', '4cf0efbd-2f6f-4586-9bbf-e2aea735fe74', 'http://localhost:3000/uploads/seed/feature.svg', 'Tokyo特色一', 'http://localhost:3000/uploads/seed/feature.svg', 'Tokyo特色二', 'http://localhost:3000/uploads/seed/feature.svg', 'Tokyo特色三', 'Day1: Tokyo行程1,Day2: Tokyo行程2,Day3: Tokyo行程3', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('3298a11c-e3de-4353-ac17-0e5be49a710c', '474a2d5e-8dda-40fa-83bf-a80f646b33eb', 'http://localhost:3000/uploads/seed/feature.svg', 'Bangkok特色一', 'http://localhost:3000/uploads/seed/feature.svg', 'Bangkok特色二', 'http://localhost:3000/uploads/seed/feature.svg', 'Bangkok特色三', 'Day1: Bangkok行程1,Day2: Bangkok行程2,Day3: Bangkok行程3', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('0b9fae95-c0d3-4b05-bc09-2f2730cfda47', '6b7ee8db-b242-4e34-8c22-33c111662feb', 'http://localhost:3000/uploads/seed/feature.svg', 'Kyoto特色一', 'http://localhost:3000/uploads/seed/feature.svg', 'Kyoto特色二', 'http://localhost:3000/uploads/seed/feature.svg', 'Kyoto特色三', 'Day1: Kyoto行程1,Day2: Kyoto行程2,Day3: Kyoto行程3', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('85ff9376-d89e-41ea-ad0f-e520076fc027', 'fb300345-ba38-48f2-be6e-b16c4380d642', 'http://localhost:3000/uploads/seed/feature.svg', 'London特色一', 'http://localhost:3000/uploads/seed/feature.svg', 'London特色二', 'http://localhost:3000/uploads/seed/feature.svg', 'London特色三', 'Day1: London行程1,Day2: London行程2,Day3: London行程3', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('fa627b5f-09f3-4b89-9a06-d9efaa6aa64f', '6fc80f12-46ab-4e4c-b6b2-47056d7d0403', 'http://localhost:3000/uploads/seed/feature.svg', 'Singapore特色一', 'http://localhost:3000/uploads/seed/feature.svg', 'Singapore特色二', 'http://localhost:3000/uploads/seed/feature.svg', 'Singapore特色三', 'Day1: Singapore行程1,Day2: Singapore行程2,Day3: Singapore行程3', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('7c8c0c2b-91d6-49ec-855c-89b63045a779', '144d34ec-2c8c-491f-9f7c-def1351e49d6', 'http://localhost:3000/uploads/seed/feature.svg', 'Okinawa特色一', 'http://localhost:3000/uploads/seed/feature.svg', 'Okinawa特色二', 'http://localhost:3000/uploads/seed/feature.svg', 'Okinawa特色三', 'Day1: Okinawa行程1,Day2: Okinawa行程2,Day3: Okinawa行程3', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('20582df1-640d-40c8-8ff7-f2087b89e471', '581c88ef-479d-4aea-9330-d83ed9c2ba71', 'http://localhost:3000/uploads/seed/feature.svg', 'Bali特色一', 'http://localhost:3000/uploads/seed/feature.svg', 'Bali特色二', 'http://localhost:3000/uploads/seed/feature.svg', 'Bali特色三', 'Day1: Bali行程1,Day2: Bali行程2,Day3: Bali行程3', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('27cd7f92-2d34-4c09-91bf-754afbe6e437', 'ed54e664-c3e4-4d1d-a937-091b65b2085f', 'http://localhost:3000/uploads/seed/feature.svg', 'Hanoi特色一', 'http://localhost:3000/uploads/seed/feature.svg', 'Hanoi特色二', 'http://localhost:3000/uploads/seed/feature.svg', 'Hanoi特色三', 'Day1: Hanoi行程1,Day2: Hanoi行程2,Day3: Hanoi行程3', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('528ee95e-23e0-4290-988d-01a4e3f33963', 'd67415c9-fd5e-4d84-8a11-7afab5d84ba3', 'http://localhost:3000/uploads/seed/feature.svg', 'Busan特色一', 'http://localhost:3000/uploads/seed/feature.svg', 'Busan特色二', 'http://localhost:3000/uploads/seed/feature.svg', 'Busan特色三', 'Day1: Busan行程1,Day2: Busan行程2,Day3: Busan行程3', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
ON CONFLICT DO NOTHING;

----- 7. 美食專區資料 "restaurant"
INSERT INTO "restaurant" (restaurant_id, tour_id, reservation_limit, website_info, website_url, created_at, updated_at) VALUES
('5ff417e4-2110-4573-98a7-2d3bc59905de', '85f6fdfb-7a95-4379-8fd3-568b0810b46e', 50, '大阪當地超人氣餐廳集合，無需排隊即可入場。', 'https://example.com/osaka-food-tour', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('676b1505-23b6-4c66-a672-509dc3da3e42', 'b6e2735c-db96-4497-a197-e56c52e2aa64', 30, '高雄夜市美食攻略，預約即享專屬美食地圖。', 'https://example.com/kaohsiung-food-tour', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('7d6115c5-b45e-4d67-85f7-5bb9128f5854', '7d6b03fa-e9bb-497d-8962-975ae377ca50', 40, 'Tainan在地人氣店家集合，預約即享專屬美食地圖。', 'https://example.com/extra-food-tour-1', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('db6897e5-2541-415a-bf80-bd991fe27d4a', '4cf0efbd-2f6f-4586-9bbf-e2aea735fe74', 40, 'Tokyo在地人氣店家集合，預約即享專屬美食地圖。', 'https://example.com/extra-food-tour-2', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('7994a01f-bacc-4de8-98db-454bb66106dc', '474a2d5e-8dda-40fa-83bf-a80f646b33eb', 40, 'Bangkok在地人氣店家集合，預約即享專屬美食地圖。', 'https://example.com/extra-food-tour-3', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
ON CONFLICT DO NOTHING;

----- 8. 美食專區營業資料 "restaurant_business"
INSERT INTO "restaurant_business" (restaurant_business_id, restaurant_id, week, business_hours, created_at, updated_at) VALUES
('08ec7145-6f86-472b-bb2a-762444cc2694', '5ff417e4-2110-4573-98a7-2d3bc59905de', 'Monday', '11:00~14:00, 17:00~21:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('e28f5ae9-28a6-41c6-b1c1-08afa5b732e4', '5ff417e4-2110-4573-98a7-2d3bc59905de', 'Tuesday', '11:00~14:00, 17:00~21:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('d4b33051-98c3-4f4c-b292-0113ee86a0e4', '5ff417e4-2110-4573-98a7-2d3bc59905de', 'Wednesday', '11:00~14:00, 17:00~21:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cffceb46-9ef1-4f2d-8385-f9e8e71509c6', '5ff417e4-2110-4573-98a7-2d3bc59905de', 'Thursday', '11:00~14:00, 17:00~21:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('6b6310a7-4fd5-477f-9a89-0ac583242807', '5ff417e4-2110-4573-98a7-2d3bc59905de', 'Friday', '11:00~14:00, 17:00~22:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('b4aa62c9-dd89-448d-8ae4-62435cc272fe', '5ff417e4-2110-4573-98a7-2d3bc59905de', 'Saturday', '11:00~15:00, 17:00~22:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('4ad307fa-7897-4447-afe3-370d5d951da8', '5ff417e4-2110-4573-98a7-2d3bc59905de', 'Sunday', '11:00~15:00, 17:00~21:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('8c324e2f-10f8-41af-8e45-b38de3432575', '676b1505-23b6-4c66-a672-509dc3da3e42', 'Monday', '17:00~23:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('9d13291c-2c59-48bc-9228-2b9a02dee8fb', '676b1505-23b6-4c66-a672-509dc3da3e42', 'Tuesday', '17:00~23:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('68fbaac0-a823-4b95-8073-7985d4905e03', '676b1505-23b6-4c66-a672-509dc3da3e42', 'Wednesday', '17:00~23:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('04dcd32b-c32b-4fd0-8de9-f7d617076a04', '676b1505-23b6-4c66-a672-509dc3da3e42', 'Thursday', '17:00~23:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('84e35853-e76e-4bba-b96f-9dade69b0ea7', '676b1505-23b6-4c66-a672-509dc3da3e42', 'Friday', '17:00~00:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('744da75e-5d89-4fd8-a29a-ba3a3362c63e', '676b1505-23b6-4c66-a672-509dc3da3e42', 'Saturday', '17:00~00:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('4e718fce-ef40-4a92-956a-6e9366b7318f', '676b1505-23b6-4c66-a672-509dc3da3e42', 'Sunday', '17:00~23:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('bbca6844-92d5-4b53-9eec-9869d5a543c2', '7d6115c5-b45e-4d67-85f7-5bb9128f5854', 'Monday', '11:00~14:00, 17:00~21:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('31e1bdf0-b340-4cb8-919c-6c88296cd0db', '7d6115c5-b45e-4d67-85f7-5bb9128f5854', 'Tuesday', '11:00~14:00, 17:00~21:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('a721a56b-d1cc-4c5c-b8bc-e14574ae11ee', '7d6115c5-b45e-4d67-85f7-5bb9128f5854', 'Wednesday', '11:00~14:00, 17:00~21:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('e7351c7c-49a0-47be-b85e-f1ccb1c72417', '7d6115c5-b45e-4d67-85f7-5bb9128f5854', 'Thursday', '11:00~14:00, 17:00~21:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('4eb0142c-7eae-451f-85af-dedfb40413f9', '7d6115c5-b45e-4d67-85f7-5bb9128f5854', 'Friday', '11:00~14:00, 17:00~21:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('22be8cc7-8481-4189-aaf0-a2448e4979e7', '7d6115c5-b45e-4d67-85f7-5bb9128f5854', 'Saturday', '11:00~14:00, 17:00~21:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('153af4f3-c94c-45c3-9665-c2394eda222f', '7d6115c5-b45e-4d67-85f7-5bb9128f5854', 'Sunday', '11:00~14:00, 17:00~21:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('7343c76d-aeda-4c75-9ea6-a22cfb74dce0', 'db6897e5-2541-415a-bf80-bd991fe27d4a', 'Monday', '11:00~14:00, 17:00~21:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('845a6441-54d3-4508-9c89-43b6f8423908', 'db6897e5-2541-415a-bf80-bd991fe27d4a', 'Tuesday', '11:00~14:00, 17:00~21:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('7997bf07-21cc-49c7-818c-21784949ff29', 'db6897e5-2541-415a-bf80-bd991fe27d4a', 'Wednesday', '11:00~14:00, 17:00~21:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('5da1de1c-2961-4610-aa75-2a52675444c1', 'db6897e5-2541-415a-bf80-bd991fe27d4a', 'Thursday', '11:00~14:00, 17:00~21:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('01af9040-8425-4cb3-a349-ce68f245fa56', 'db6897e5-2541-415a-bf80-bd991fe27d4a', 'Friday', '11:00~14:00, 17:00~21:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cef5a831-e62e-467e-82f2-e8caf5e333d0', 'db6897e5-2541-415a-bf80-bd991fe27d4a', 'Saturday', '11:00~14:00, 17:00~21:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('57011be8-1f62-411a-ac01-bc3d092e0e41', 'db6897e5-2541-415a-bf80-bd991fe27d4a', 'Sunday', '11:00~14:00, 17:00~21:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('33e3494a-e9f2-4f7d-81f6-5cfdda9f302f', '7994a01f-bacc-4de8-98db-454bb66106dc', 'Monday', '11:00~14:00, 17:00~21:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('496ba32c-c6ce-43bc-9a36-fb050a08837b', '7994a01f-bacc-4de8-98db-454bb66106dc', 'Tuesday', '11:00~14:00, 17:00~21:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('8281cb00-4440-4256-93dd-3bf8297a376e', '7994a01f-bacc-4de8-98db-454bb66106dc', 'Wednesday', '11:00~14:00, 17:00~21:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('471cf078-9f71-423b-a284-30225306d87b', '7994a01f-bacc-4de8-98db-454bb66106dc', 'Thursday', '11:00~14:00, 17:00~21:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('ffa73135-daca-473c-8a41-9287bbf51755', '7994a01f-bacc-4de8-98db-454bb66106dc', 'Friday', '11:00~14:00, 17:00~21:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('147d3888-7b77-48dd-9bdd-de02bf607afb', '7994a01f-bacc-4de8-98db-454bb66106dc', 'Saturday', '11:00~14:00, 17:00~21:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('6c5d7535-343f-4fc7-9375-097787088b8e', '7994a01f-bacc-4de8-98db-454bb66106dc', 'Sunday', '11:00~14:00, 17:00~21:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
ON CONFLICT DO NOTHING;

----- 9. 美食專區菜單資料 "restaurant_menu"
INSERT INTO "restaurant_menu" (restaurant_menu_id, restaurant_id, name, price, description, created_at, updated_at) VALUES
('7343a14f-37d8-4249-ac43-26ac6c534aff', '5ff417e4-2110-4573-98a7-2d3bc59905de', '章魚燒', 150.0, '外酥內軟，經典大阪街頭小吃。', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('3223563d-d198-41ca-a8e5-8c5a63db7df5', '5ff417e4-2110-4573-98a7-2d3bc59905de', '大阪燒', 300.0, '層層堆疊的美味與滿滿高麗菜。', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('64c9aa03-eda6-447f-bca8-79d277e2f610', '5ff417e4-2110-4573-98a7-2d3bc59905de', '串燒拼盤', 450.0, '嚴選牛、豬、雞肉串搭配秘製醬汁。', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('6b3dea15-becb-4040-bf39-a40b46d850a6', '676b1505-23b6-4c66-a672-509dc3da3e42', '鹽酥雞', 80.0, '酥脆香嫩的經典夜市小吃。', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('f7af6d23-bdf1-46e2-9d15-c9ca11f4fc02', '676b1505-23b6-4c66-a672-509dc3da3e42', '滷味拼盤', 120.0, '多樣滷味搭配獨門滷汁，回味無窮。', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('85034e81-8be7-4316-a494-84ce2b8441b3', '676b1505-23b6-4c66-a672-509dc3da3e42', '木瓜牛奶', 70.0, '高雄人氣飲品，清甜滑順解渴。', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('b04f48d6-e2e7-49e0-aa9d-80d68f96c696', '7d6115c5-b45e-4d67-85f7-5bb9128f5854', 'Tainan招牌小吃', 120.0, 'Tainan在地人推薦。', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('b7778e24-7548-4b6b-9f7a-a385f469f870', '7d6115c5-b45e-4d67-85f7-5bb9128f5854', 'Tainan特調飲品', 80.0, 'Tainan在地人推薦。', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('ce0aba09-143f-4f8a-a5c7-754c987e88a2', 'db6897e5-2541-415a-bf80-bd991fe27d4a', 'Tokyo招牌小吃', 120.0, 'Tokyo在地人推薦。', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('5a95794f-9be3-4b70-a3d0-deb18d67ee10', 'db6897e5-2541-415a-bf80-bd991fe27d4a', 'Tokyo特調飲品', 80.0, 'Tokyo在地人推薦。', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('a2afb489-b8a6-4b7d-927a-d7247d5b7c31', '7994a01f-bacc-4de8-98db-454bb66106dc', 'Bangkok招牌小吃', 120.0, 'Bangkok在地人推薦。', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('ae575690-c166-4216-b801-07822f1d941b', '7994a01f-bacc-4de8-98db-454bb66106dc', 'Bangkok特調飲品', 80.0, 'Bangkok在地人推薦。', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
ON CONFLICT DO NOTHING;

---- 10. 飯店專區資料 "hotel"
INSERT INTO "hotel" (hotel_id, tour_id, facility_desc, food_desc, room_desc, leisure_desc, traffic_desc, other_desc, created_at, updated_at) VALUES
('752f2728-0493-4c48-af06-815bff568699', '1692beb1-be37-4a73-93e4-89d0adf1250c', '24 小時櫃台服務, 免費 Wi-Fi, 行李寄存服務, 毛巾, 客房清潔服務', '早餐供應, 餐廳/咖啡館, 飲水機', '冷氣/暖氣, 獨立衛浴, 電視（有線/第四台）, 小冰箱', '健身房, SPA/按摩服務, 游泳池（室外）', '停車場, 租車服務, 接駁巴士（市區）', '外幣兌換, 叫車/叫計程車, 洗衣服務/自助洗衣', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('bd4a4c92-9cc0-422e-b735-f514be62acc1', '9486ac9a-ab9d-4282-a6db-03fb0ccc84c7', '24 小時櫃台服務, 免費 Wi-Fi, 行李寄存服務, 提供嬰兒床/收嬰', '早餐供應, 酒吧或 Lounge 酒廊', '冷氣/暖氣, 獨立衛浴, 電視（有線/第四台）, 咖啡機/加熱水壺', '健身房, 兒童遊戲區, 娛樂區/圖書館', '停車場, 租車服務, 機場接送服務（需預約）', '外幣兌換, 褓姆服務/吸菸區', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('ccc4d6e6-d3b2-4fe7-b9c2-ce13eddd4e22', '144d34ec-2c8c-491f-9f7c-def1351e49d6', '24 小時櫃台服務, 免費 Wi-Fi, 行李寄存服務', '早餐供應', '冷氣/暖氣, 獨立衛浴', '游泳池（室外）', '接駁巴士（市區）', '叫車/叫計程車', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('a2a6ffbf-980d-44d7-bc19-6f3c863b9748', '581c88ef-479d-4aea-9330-d83ed9c2ba71', '24 小時櫃台服務, 免費 Wi-Fi, 行李寄存服務', '早餐供應', '冷氣/暖氣, 獨立衛浴', '游泳池（室外）', '接駁巴士（市區）', '叫車/叫計程車', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('d41dca43-861d-4e9e-ba6a-593331050a48', 'ed54e664-c3e4-4d1d-a937-091b65b2085f', '24 小時櫃台服務, 免費 Wi-Fi, 行李寄存服務', '早餐供應', '冷氣/暖氣, 獨立衛浴', '游泳池（室外）', '接駁巴士（市區）', '叫車/叫計程車', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('5eb2eb03-778e-4012-b21d-cc8eeec53976', 'd67415c9-fd5e-4d84-8a11-7afab5d84ba3', '24 小時櫃台服務, 免費 Wi-Fi, 行李寄存服務', '早餐供應', '冷氣/暖氣, 獨立衛浴', '游泳池（室外）', '接駁巴士（市區）', '叫車/叫計程車', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
ON CONFLICT DO NOTHING;

---- 11. 飯店專區客房資料 "hotel_room"
INSERT INTO "hotel_room" (hotel_room_id, hotel_id, title, capacity, room_count, image, image_desc, created_at, updated_at) VALUES
('3d1567bd-86f4-4db8-823d-5515e5133a43', '752f2728-0493-4c48-af06-815bff568699', '設計雙人房', 2, 10, 'http://localhost:3000/uploads/seed/tour.svg', '現代簡約風格，附舒適大床與書桌。', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('98a73337-46c6-4c87-90b4-2a8c5a2bfb78', '752f2728-0493-4c48-af06-815bff568699', '豪華家庭房', 4, 5, 'http://localhost:3000/uploads/seed/tour.svg', '寬敞空間，適合親子同住，附沙發床。', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('04f5623f-fc77-490d-95b9-1c2c2fbb6fb9', 'bd4a4c92-9cc0-422e-b735-f514be62acc1', '自然雙人房', 2, 8, 'http://localhost:3000/uploads/seed/tour.svg', '溫暖木質設計，大面窗採光。', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('d0d3f2fb-614d-4463-b192-10c0a84915ba', 'bd4a4c92-9cc0-422e-b735-f514be62acc1', '親子套房', 4, 6, 'http://localhost:3000/uploads/seed/tour.svg', '親子專用設施，兒童遊戲空間。', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('a8079bf2-187a-44d3-96d1-bf25c90fd4a5', 'ccc4d6e6-d3b2-4fe7-b9c2-ce13eddd4e22', '海景雙人房', 2, 6, 'http://localhost:3000/uploads/seed/tour.svg', 'Okinawa客房', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('95385cf9-21b3-40c2-a66e-e8a4689eb156', 'ccc4d6e6-d3b2-4fe7-b9c2-ce13eddd4e22', '海景家庭房', 4, 6, 'http://localhost:3000/uploads/seed/tour.svg', 'Okinawa客房', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('307e6e54-b515-4271-9eb3-74d1b3672e36', 'a2a6ffbf-980d-44d7-bc19-6f3c863b9748', 'Bali雙人房', 2, 6, 'http://localhost:3000/uploads/seed/tour.svg', 'Bali客房', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('afbea4e0-a9c3-4119-bd50-305e1588bc03', 'a2a6ffbf-980d-44d7-bc19-6f3c863b9748', 'Bali家庭房', 4, 6, 'http://localhost:3000/uploads/seed/tour.svg', 'Bali客房', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('d3b0f657-66ac-4310-af7e-ddce86ba67b8', 'd41dca43-861d-4e9e-ba6a-593331050a48', 'Hanoi雙人房', 2, 6, 'http://localhost:3000/uploads/seed/tour.svg', 'Hanoi客房', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('2765f258-67f0-4738-903c-b98dc1d1ab8e', 'd41dca43-861d-4e9e-ba6a-593331050a48', 'Hanoi家庭房', 4, 6, 'http://localhost:3000/uploads/seed/tour.svg', 'Hanoi客房', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('5caa744b-6957-47a4-9a93-d6624c93e4ef', '5eb2eb03-778e-4012-b21d-cc8eeec53976', 'Busan雙人房', 2, 6, 'http://localhost:3000/uploads/seed/tour.svg', 'Busan客房', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('173cd61f-1fd5-4c9d-ba33-217e3a801a01', '5eb2eb03-778e-4012-b21d-cc8eeec53976', 'Busan家庭房', 4, 6, 'http://localhost:3000/uploads/seed/tour.svg', 'Busan客房', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
ON CONFLICT DO NOTHING;

---- 12. 重要通知資料(促銷/異動) "notification"
INSERT INTO "notification" (notification_id, tour_id, type, start_date, end_date, discount, promo_price, change_desc, created_at, updated_at) VALUES
('7541baf4-6e07-4a18-8d25-debe3aa279c0', 'c35e011b-ffe4-48ea-8511-9f27ef0d5d69', '促銷', (TIMESTAMP '2025-05-10 00:00:00' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), (TIMESTAMP '2025-06-09 23:59:59' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), 10.0, 40500.0, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('c7ffe61d-7392-4bd0-b8b2-57fa7fa88f8c', '9fd27d62-39ba-4b57-8015-6cfc47bb0a52', '促銷', (TIMESTAMP '2025-05-15 00:00:00' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), (TIMESTAMP '2025-06-14 23:59:59' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), 15.0, 83300.0, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('0c143649-830c-4f23-95bd-bbe3fcb2bbc6', '8c74c63e-933e-4623-aa4c-f3814db9c6c2', '異動', NULL, NULL, NULL, NULL, '因故調整行程，第4日改至比薩市區自由行。', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('33723c8c-6281-4309-baf2-f747512dc771', 'f7cdc48d-7443-4b5b-b12a-31a5fa287dd2', '異動', NULL, NULL, NULL, NULL, '新增米佛峽灣遊船行程，行程時間延長1天。', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('4345a16b-1ef9-4516-b021-5855a2422314', 'dfe1a4a5-f228-4ac2-820b-fd8e96b7fd33', '促銷', (TIMESTAMP '2025-05-13 00:00:00' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), (TIMESTAMP '2025-06-03 23:59:59' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), 10.0, 108000.0, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('4009ece0-e2b6-40fd-be34-c3e51c8402c1', 'c2e03b7d-b117-4bea-94d6-59e753b00d90', '促銷', (TIMESTAMP '2025-05-17 00:00:00' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), (TIMESTAMP '2025-06-19 23:59:59' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), 20.0, 88000.0, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('342d0c24-665e-435f-9dff-174c1103d75f', '9d2e5cdc-230a-4a0a-a7d5-4eb00039fed0', '促銷', (TIMESTAMP '2025-05-19 00:00:00' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), (TIMESTAMP '2025-05-27 23:59:59' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), 10.0, 81000.0, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('561d5c15-cd76-4bc2-99ec-b96ecceea484', '7d6b03fa-e9bb-497d-8962-975ae377ca50', '促銷', (TIMESTAMP '2025-05-30 00:00:00' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), (TIMESTAMP '2025-06-29 23:59:59' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), 10.0, 2700.0, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('a41f594b-db19-453c-a220-6fef4ad87ed3', '6b7ee8db-b242-4e34-8c22-33c111662feb', '促銷', (TIMESTAMP '2025-04-10 00:00:00' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), (TIMESTAMP '2025-05-10 23:59:59' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), 10.0, 5400.0, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
ON CONFLICT DO NOTHING;

---- 13. 國家資料 "country"
INSERT INTO "country" (country_id, name, created_at) VALUES
('74931c64-738c-409d-aed9-9de3c5caf477', '台灣', CURRENT_TIMESTAMP),
('01551936-7959-47fa-8c59-bd90b9e8f285', '日本', CURRENT_TIMESTAMP),
('f76086a0-5b90-4813-a944-2baf0f2ee403', '韓國', CURRENT_TIMESTAMP),
('fd79e73d-e9e1-41f2-87b7-ddfcd15cc008', '香港', CURRENT_TIMESTAMP),
('0a5ca600-d84f-462a-9cec-1218f75e962f', '澳門', CURRENT_TIMESTAMP),
('03eba4d1-1324-4ba5-b92a-0e441761e934', '中國', CURRENT_TIMESTAMP),
('ba845924-3cbb-4da8-b7a5-f82b70c2073a', '泰國', CURRENT_TIMESTAMP),
('ca82b89c-ce39-44d9-9f03-513ba05cf8e4', '越南', CURRENT_TIMESTAMP),
('37779b60-e6e4-45ba-95bc-f115b1975349', '新加坡', CURRENT_TIMESTAMP),
('d2698bec-3730-4407-927b-8d1331f9a222', '馬來西亞', CURRENT_TIMESTAMP),
('a8464a54-14e4-44e5-b1a0-e4cfae6e8788', '印尼', CURRENT_TIMESTAMP),
('d99e61f8-ae7e-413b-91dc-ff238aaba61c', '菲律賓', CURRENT_TIMESTAMP),
('3b2881b6-1bad-41f9-b31b-942fee65e0d9', '印度', CURRENT_TIMESTAMP),
('6a0cad36-fa0c-473b-85c1-a22309d170cc', '英國', CURRENT_TIMESTAMP),
('6e0465c7-907b-4d1b-ab97-b52d83ffd751', '法國', CURRENT_TIMESTAMP),
('c377ee6a-289a-418a-b5d5-0c52d3308af1', '德國', CURRENT_TIMESTAMP),
('3f30ae94-b44f-494b-b30e-f0dabd9153af', '義大利', CURRENT_TIMESTAMP),
('a175fe81-1e6c-4263-a0c2-e731443a2d28', '西班牙', CURRENT_TIMESTAMP),
('fe8ae07c-25e3-43ef-bf75-1a531da050f5', '瑞士', CURRENT_TIMESTAMP),
('5d6b22bf-ff52-4fbc-96c5-75f79c751422', '荷蘭', CURRENT_TIMESTAMP),
('7d5740d0-c23c-44cd-ade7-2523aaa308ca', '捷克', CURRENT_TIMESTAMP),
('20d5aa1a-56f4-4469-afd8-4f5a87e6ea15', '奧地利', CURRENT_TIMESTAMP),
('a657383f-e5bb-4d58-9e1c-733c500cb48c', '芬蘭', CURRENT_TIMESTAMP),
('f4146a4b-6935-4200-8488-98d6fb59ea14', '冰島', CURRENT_TIMESTAMP),
('cc1d945c-c9f3-4c9b-98c2-c63ea9a92168', '挪威', CURRENT_TIMESTAMP),
('067c3ffb-6cf1-46a0-816a-5f32babfd890', '丹麥', CURRENT_TIMESTAMP),
('b0e13f64-18f8-4a62-be1f-709a7b6cf9ee', '希臘', CURRENT_TIMESTAMP),
('e467795b-9538-4d3d-ab88-0ccc798e70e7', '美國', CURRENT_TIMESTAMP),
('0564470e-7368-473f-9bf1-c185347e069d', '加拿大', CURRENT_TIMESTAMP),
('d1e219d0-75ed-488a-a642-0a60942f197d', '墨西哥', CURRENT_TIMESTAMP),
('aec2b95a-868e-4dbd-b1a1-9729dee75c27', '巴西', CURRENT_TIMESTAMP),
('b2dc7569-91cf-42b5-9dd6-5ac0d0b3a6a9', '澳大利亞', CURRENT_TIMESTAMP),
('d7625dc7-b9bf-41be-9a35-1619f581a8d0', '紐西蘭', CURRENT_TIMESTAMP),
('202331aa-548b-4064-97c2-72c2acccae6e', '阿聯酋', CURRENT_TIMESTAMP),
('c55ce9a3-9f23-467b-905a-8c4ebc46c294', '土耳其', CURRENT_TIMESTAMP),
('6e4b7a7c-3b5c-428d-810c-3010e45bf76d', '埃及', CURRENT_TIMESTAMP),
('ae1e8fd8-2112-4581-a338-8a7e9338fc1f', '南非', CURRENT_TIMESTAMP)
ON CONFLICT DO NOTHING;

---- 14. 地區資料 "region"
INSERT INTO "region" (region_id, country_id, name, created_at) VALUES
('9f14c408-05d8-4876-9a98-c5578f241f43', '74931c64-738c-409d-aed9-9de3c5caf477', '台北市', CURRENT_TIMESTAMP),
('8a5e6a16-2c86-4fbc-8521-c1e58cf12eaa', '74931c64-738c-409d-aed9-9de3c5caf477', '新北市', CURRENT_TIMESTAMP),
('4186a3da-f781-4f91-980f-bd050da0bb9e', '74931c64-738c-409d-aed9-9de3c5caf477', '桃園市', CURRENT_TIMESTAMP),
('4179cfda-9108-4433-ada4-ef97248c0c15', '74931c64-738c-409d-aed9-9de3c5caf477', '台中市', CURRENT_TIMESTAMP),
('6740be16-7d9a-466d-ad76-9531def5afb4', '74931c64-738c-409d-aed9-9de3c5caf477', '台南市', CURRENT_TIMESTAMP),
('f82920a2-b275-4dbc-a02e-98512104469c', '74931c64-738c-409d-aed9-9de3c5caf477', '高雄市', CURRENT_TIMESTAMP),
('4236cc2a-01cd-4a31-9f97-396c5cab1e4d', '74931c64-738c-409d-aed9-9de3c5caf477', '基隆市', CURRENT_TIMESTAMP),
('cd4ae8ca-2517-4a03-a58d-bfa2728d8bca', '74931c64-738c-409d-aed9-9de3c5caf477', '新竹市', CURRENT_TIMESTAMP),
('1bf393e2-7fdd-42af-a09e-95575513b860', '74931c64-738c-409d-aed9-9de3c5caf477', '新竹縣', CURRENT_TIMESTAMP),
('2992afc3-2141-434e-89f8-3c2c268f6906', '74931c64-738c-409d-aed9-9de3c5caf477', '苗栗縣', CURRENT_TIMESTAMP),
('45c41418-e3ab-4ede-8faa-70c5f527b4fd', '74931c64-738c-409d-aed9-9de3c5caf477', '彰化縣', CURRENT_TIMESTAMP),
('fc0bd5de-5a53-4157-9b64-509333e96c64', '74931c64-738c-409d-aed9-9de3c5caf477', '南投縣', CURRENT_TIMESTAMP),
('df3276e1-22c3-491b-a85c-c5c6c851af45', '74931c64-738c-409d-aed9-9de3c5caf477', '雲林縣', CURRENT_TIMESTAMP),
('a7019f5b-0550-4c97-9c52-2a9137758144', '74931c64-738c-409d-aed9-9de3c5caf477', '嘉義市', CURRENT_TIMESTAMP),
('3e71ef36-cde4-4953-b4a1-b15ec1330cd2', '74931c64-738c-409d-aed9-9de3c5caf477', '嘉義縣', CURRENT_TIMESTAMP),
('9c35bbd2-260b-445e-9540-f2f458195db1', '74931c64-738c-409d-aed9-9de3c5caf477', '屏東縣', CURRENT_TIMESTAMP),
('e0dbe388-b260-4002-96c1-0996821a4a9a', '74931c64-738c-409d-aed9-9de3c5caf477', '宜蘭縣', CURRENT_TIMESTAMP),
('e0057dd1-fffb-4036-8e84-2235d394646d', '74931c64-738c-409d-aed9-9de3c5caf477', '花蓮縣', CURRENT_TIMESTAMP),
('38f1c151-ce30-421b-869a-aa4604b8a817', '74931c64-738c-409d-aed9-9de3c5caf477', '台東縣', CURRENT_TIMESTAMP),
('da443240-9875-499b-87b8-5aa39bb7d7c0', '74931c64-738c-409d-aed9-9de3c5caf477', '澎湖縣', CURRENT_TIMESTAMP),
('40950a4c-7ef0-4a85-80c9-43b30684b705', '74931c64-738c-409d-aed9-9de3c5caf477', '金門縣', CURRENT_TIMESTAMP),
('c9e8f29c-0ca2-4338-8a08-5bb35d387b36', '74931c64-738c-409d-aed9-9de3c5caf477', '連江縣', CURRENT_TIMESTAMP),
('32d03de9-2057-4fd8-b292-70e02f2a7d48', '01551936-7959-47fa-8c59-bd90b9e8f285', '東京', CURRENT_TIMESTAMP),
('5b132553-3fbb-43c3-808a-8984d492b704', '01551936-7959-47fa-8c59-bd90b9e8f285', '大阪', CURRENT_TIMESTAMP),
('989af651-5995-4efa-82d5-de879bce8e20', '01551936-7959-47fa-8c59-bd90b9e8f285', '京都', CURRENT_TIMESTAMP),
('86bb0930-0cc6-4a38-8d0f-629fbdabcbc6', '01551936-7959-47fa-8c59-bd90b9e8f285', '北海道', CURRENT_TIMESTAMP),
('48236371-5bff-4bbc-afe3-35472c3ab43f', '01551936-7959-47fa-8c59-bd90b9e8f285', '沖繩', CURRENT_TIMESTAMP),
('78b9b2a7-e72b-4b7a-a484-8ad4ab5bb17b', 'f76086a0-5b90-4813-a944-2baf0f2ee403', '首爾', CURRENT_TIMESTAMP),
('20f715b2-d859-4231-bfd8-a731ca727b4d', 'f76086a0-5b90-4813-a944-2baf0f2ee403', '釜山', CURRENT_TIMESTAMP),
('d62a70c8-fd58-4029-bf83-213f8dd15db1', 'f76086a0-5b90-4813-a944-2baf0f2ee403', '濟州島', CURRENT_TIMESTAMP),
('c110d3a7-4eaa-4b38-80c8-ed65c649b29a', 'fd79e73d-e9e1-41f2-87b7-ddfcd15cc008', '香港島', CURRENT_TIMESTAMP),
('e132bcf3-0885-46d5-8821-ed43ad8f567c', 'fd79e73d-e9e1-41f2-87b7-ddfcd15cc008', '九龍', CURRENT_TIMESTAMP),
('33150f89-cf16-4734-9ab2-fb6084a67a4d', 'fd79e73d-e9e1-41f2-87b7-ddfcd15cc008', '新界', CURRENT_TIMESTAMP),
('609ed962-1a50-4fc2-82e9-68861843b90f', '0a5ca600-d84f-462a-9cec-1218f75e962f', '澳門半島', CURRENT_TIMESTAMP),
('2ede1617-b4f8-49c7-b874-358f20dceea5', '0a5ca600-d84f-462a-9cec-1218f75e962f', '氹仔', CURRENT_TIMESTAMP),
('8e533242-51d7-441c-b46b-d601d1ba13b6', '0a5ca600-d84f-462a-9cec-1218f75e962f', '路氹城', CURRENT_TIMESTAMP),
('675e60d3-8b24-42b4-9e85-73b859b8e5dc', '03eba4d1-1324-4ba5-b92a-0e441761e934', '北京', CURRENT_TIMESTAMP),
('fbd97e73-b09d-4965-93af-154990b21c8a', '03eba4d1-1324-4ba5-b92a-0e441761e934', '上海', CURRENT_TIMESTAMP),
('34a49b3e-1e23-4226-9d49-67923b6850f4', '03eba4d1-1324-4ba5-b92a-0e441761e934', '廣州', CURRENT_TIMESTAMP),
('20119660-28b0-466d-b164-e990c14bfacf', '03eba4d1-1324-4ba5-b92a-0e441761e934', '成都', CURRENT_TIMESTAMP),
('1b978ff4-4b37-423b-9d9a-757dcb996910', '03eba4d1-1324-4ba5-b92a-0e441761e934', '西安', CURRENT_TIMESTAMP),
('cc67bbab-cbbd-4551-b66e-967289cf4381', 'e467795b-9538-4d3d-ab88-0ccc798e70e7', '紐約', CURRENT_TIMESTAMP),
('23701d40-9d2e-4ae2-aead-d0de800d2f59', 'e467795b-9538-4d3d-ab88-0ccc798e70e7', '洛杉磯', CURRENT_TIMESTAMP),
('ebd51aae-7167-4e56-a3f3-06aa88a0afb0', 'e467795b-9538-4d3d-ab88-0ccc798e70e7', '舊金山', CURRENT_TIMESTAMP),
('5ff5b2d0-2beb-4cea-baf7-14c138e0196f', 'e467795b-9538-4d3d-ab88-0ccc798e70e7', '拉斯維加斯', CURRENT_TIMESTAMP),
('b10822b9-6d52-4179-9055-7dc774f0cf38', 'e467795b-9538-4d3d-ab88-0ccc798e70e7', '夏威夷', CURRENT_TIMESTAMP),
('0f990152-a71d-4321-b88d-9af3ee4ad098', '6a0cad36-fa0c-473b-85c1-a22309d170cc', '倫敦', CURRENT_TIMESTAMP),
('81479520-6d87-4288-8567-82d50dfa0ef2', '6a0cad36-fa0c-473b-85c1-a22309d170cc', '曼徹斯特', CURRENT_TIMESTAMP),
('9534f5fd-dacd-4190-8cc9-3edcd4c568d6', '6a0cad36-fa0c-473b-85c1-a22309d170cc', '愛丁堡', CURRENT_TIMESTAMP),
('0fcad61a-d778-49c1-8382-46349b0bbd45', '6e0465c7-907b-4d1b-ab97-b52d83ffd751', '巴黎', CURRENT_TIMESTAMP),
('fc48ad89-b12c-4d40-805b-78fe39ca8c1f', '6e0465c7-907b-4d1b-ab97-b52d83ffd751', '里昂', CURRENT_TIMESTAMP),
('cd93d75c-e62f-4ea5-948a-59f045171409', '6e0465c7-907b-4d1b-ab97-b52d83ffd751', '尼斯', CURRENT_TIMESTAMP),
('0078c22e-282c-4da9-80e0-d9e7a50521d1', 'ba845924-3cbb-4da8-b7a5-f82b70c2073a', '曼谷', CURRENT_TIMESTAMP),
('829821df-cc03-4158-a4d8-ce233e003556', 'ba845924-3cbb-4da8-b7a5-f82b70c2073a', '清邁', CURRENT_TIMESTAMP),
('52523ed6-1538-415b-b67f-f53eeb7fd84b', 'ba845924-3cbb-4da8-b7a5-f82b70c2073a', '普吉島', CURRENT_TIMESTAMP),
('7e5e778d-3132-4634-ac6e-9c3965e44641', 'ba845924-3cbb-4da8-b7a5-f82b70c2073a', '芭達雅', CURRENT_TIMESTAMP),
('f8634c1e-1f35-40f0-a81c-f5757f191911', 'ca82b89c-ce39-44d9-9f03-513ba05cf8e4', '胡志明市', CURRENT_TIMESTAMP),
('4c8efe62-b462-4167-b0ec-862cc4e213b4', 'ca82b89c-ce39-44d9-9f03-513ba05cf8e4', '河內', CURRENT_TIMESTAMP),
('8c46f2ed-243a-4886-97bb-43fd53026f5a', 'ca82b89c-ce39-44d9-9f03-513ba05cf8e4', '峴港', CURRENT_TIMESTAMP),
('f8729d5a-7968-4afb-af6e-bf92e0967a39', '37779b60-e6e4-45ba-95bc-f115b1975349', '新加坡', CURRENT_TIMESTAMP),
('c3dea9e0-e839-4d12-9555-a966033415af', 'd2698bec-3730-4407-927b-8d1331f9a222', '吉隆坡', CURRENT_TIMESTAMP),
('b1f90eb3-a7d3-49e3-b1f7-d2130b3761d3', 'd2698bec-3730-4407-927b-8d1331f9a222', '檳城', CURRENT_TIMESTAMP),
('3994316d-a85c-491b-a720-9b05eee5550b', 'd2698bec-3730-4407-927b-8d1331f9a222', '沙巴', CURRENT_TIMESTAMP),
('95a41233-f9bc-45a0-a00d-c381e53ab4c4', 'a8464a54-14e4-44e5-b1a0-e4cfae6e8788', '峇里島', CURRENT_TIMESTAMP),
('0d53362b-d3ec-4e1f-8978-b361097be636', 'a8464a54-14e4-44e5-b1a0-e4cfae6e8788', '雅加達', CURRENT_TIMESTAMP),
('60194fa0-ee71-4f1c-a171-d7eec40f5319', 'd99e61f8-ae7e-413b-91dc-ff238aaba61c', '馬尼拉', CURRENT_TIMESTAMP),
('fe5d2aa0-4317-43fa-865e-9445bf2288ce', 'd99e61f8-ae7e-413b-91dc-ff238aaba61c', '宿霧', CURRENT_TIMESTAMP),
('7b630a09-d892-4980-876a-2ffa6ff88aa8', 'd99e61f8-ae7e-413b-91dc-ff238aaba61c', '長灘島', CURRENT_TIMESTAMP),
('ac33c2a8-a4e1-40d4-ad77-0024b323f349', '3b2881b6-1bad-41f9-b31b-942fee65e0d9', '德里', CURRENT_TIMESTAMP),
('0464999d-b09f-4e70-8ed3-f43420cc6b14', '3b2881b6-1bad-41f9-b31b-942fee65e0d9', '孟買', CURRENT_TIMESTAMP),
('5c679f39-6438-4c53-b107-01248489fbce', '3b2881b6-1bad-41f9-b31b-942fee65e0d9', '齋浦爾', CURRENT_TIMESTAMP),
('a8d45268-7579-444c-bb76-5de3900d71e7', 'b2dc7569-91cf-42b5-9dd6-5ac0d0b3a6a9', '雪梨', CURRENT_TIMESTAMP),
('39da7444-da19-4288-8546-4b9bcc7636b3', 'b2dc7569-91cf-42b5-9dd6-5ac0d0b3a6a9', '墨爾本', CURRENT_TIMESTAMP),
('7e9f2690-fb8b-4d7d-9075-5bad8a4ce90e', 'b2dc7569-91cf-42b5-9dd6-5ac0d0b3a6a9', '布里斯本', CURRENT_TIMESTAMP),
('58e2da54-d80f-4477-a5e3-00b8af91f6a2', 'b2dc7569-91cf-42b5-9dd6-5ac0d0b3a6a9', '黃金海岸', CURRENT_TIMESTAMP),
('b7c826d4-29f9-4c4d-af78-90ef3f2b9303', 'd7625dc7-b9bf-41be-9a35-1619f581a8d0', '奧克蘭', CURRENT_TIMESTAMP),
('f38aee30-881c-4cbf-a318-7af1c8a6ed7d', 'd7625dc7-b9bf-41be-9a35-1619f581a8d0', '皇后鎮', CURRENT_TIMESTAMP),
('14a96646-34ea-421f-ac9e-936c3622cd05', 'd7625dc7-b9bf-41be-9a35-1619f581a8d0', '基督城', CURRENT_TIMESTAMP),
('96d431cc-2cde-4e9d-a9ad-ad0c9b14891b', '202331aa-548b-4064-97c2-72c2acccae6e', '杜拜', CURRENT_TIMESTAMP),
('ba2a5c60-a0a4-47e7-b1c2-e205e60ae5b3', '202331aa-548b-4064-97c2-72c2acccae6e', '阿布達比', CURRENT_TIMESTAMP),
('455d587e-6c18-4bca-89bd-9e5c960d23cf', 'c55ce9a3-9f23-467b-905a-8c4ebc46c294', '伊斯坦堡', CURRENT_TIMESTAMP),
('bb2c614a-8e1d-4cbf-a33c-51be77da6a9f', 'c55ce9a3-9f23-467b-905a-8c4ebc46c294', '卡帕多奇亞', CURRENT_TIMESTAMP),
('7d86e069-38ab-463f-b133-b8d0d33268e3', 'c55ce9a3-9f23-467b-905a-8c4ebc46c294', '安塔利亞', CURRENT_TIMESTAMP),
('431b0339-8372-4805-a677-a0104bf495b6', '6e4b7a7c-3b5c-428d-810c-3010e45bf76d', '開羅', CURRENT_TIMESTAMP),
('e3c89ad4-622e-4f15-a377-ac71c846873e', '6e4b7a7c-3b5c-428d-810c-3010e45bf76d', '盧克索', CURRENT_TIMESTAMP),
('c33ecdfb-afb3-42d0-9fc4-385b4cd9cd20', 'ae1e8fd8-2112-4581-a338-8a7e9338fc1f', '開普敦', CURRENT_TIMESTAMP),
('411d2b8d-d736-4977-8eee-e6c451b4a2d9', 'ae1e8fd8-2112-4581-a338-8a7e9338fc1f', '約翰尼斯堡', CURRENT_TIMESTAMP)
ON CONFLICT DO NOTHING;

---- 15. 購物車大項目資料 "cart"
INSERT INTO cart (cart_id, user_id, total_price) VALUES
('a80300f8-e091-4f29-9faf-a1286cffc135', 'c3d1513b-b8f0-48de-b7c3-3a75485f8ae6', 6263.64),
('ad283bc8-6d9b-4130-b783-b61a1e65bc61', 'c35f34c3-337f-410b-b57a-e439a7ba969b', 3576.74),
('680fbe1a-69bc-4c10-90d3-75aefa3f16a7', '568ed618-7b23-4b88-a2fb-d519d1176a63', 6482.73)
ON CONFLICT DO NOTHING;

---- 16. 購物車細項資料 "cart_item"
INSERT INTO cart_item (cart_item_id, cart_id, tour_id, quantity, start_date, end_date, room_type) VALUES
('02a8ebc9-adc3-4d16-9a39-bd665429da30', 'ad283bc8-6d9b-4130-b783-b61a1e65bc61', 'b6e2735c-db96-4497-a197-e56c52e2aa64', 2, (TIMESTAMP '2025-06-03' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), NULL, NULL),
('6c5174dc-d167-44c7-8942-74b03c217e1d', '680fbe1a-69bc-4c10-90d3-75aefa3f16a7', '9fd27d62-39ba-4b57-8015-6cfc47bb0a52', 3, (TIMESTAMP '2025-11-10' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), (TIMESTAMP '2025-11-15' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), NULL),
('56f22e11-6202-4318-ba62-0f208f340748', '680fbe1a-69bc-4c10-90d3-75aefa3f16a7', '57bfb290-092a-40c7-a68c-7b1a032cfe64', 3, (TIMESTAMP '2025-06-09' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), (TIMESTAMP '2025-06-10' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), NULL),
('1b7ce16c-0337-4224-bac1-890ca2fe81ba', 'ad283bc8-6d9b-4130-b783-b61a1e65bc61', '8c74c63e-933e-4623-aa4c-f3814db9c6c2', 5, (TIMESTAMP '2025-10-15' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), (TIMESTAMP '2025-10-22' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), NULL),
('9a8cfce2-6ddc-4c6c-9d78-8bc4e775e1b3', 'ad283bc8-6d9b-4130-b783-b61a1e65bc61', 'f7cdc48d-7443-4b5b-b12a-31a5fa287dd2', 3, (TIMESTAMP '2025-11-05' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), (TIMESTAMP '2025-11-15' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), NULL),
('cc67db63-f035-4f45-a8c4-1fb55b928c60', 'a80300f8-e091-4f29-9faf-a1286cffc135', '85f6fdfb-7a95-4379-8fd3-568b0810b46e', 3, (TIMESTAMP '2025-06-19' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), NULL, NULL)
ON CONFLICT DO NOTHING;

---- 17. 訂單大項目資料 "orders"
INSERT INTO orders (order_id, user_id, address, phone, payment_type, discount_type, payment_status, total_price, discount_price, created_at, updated_at) VALUES
('b294a0bd-a29b-40c9-8228-721c0e31899e', 'c3d1513b-b8f0-48de-b7c3-3a75485f8ae6', '台北市中山區南京東路3段123號', '0987654321', 'credit_card', 'none', 1, 45000, NULL, CURRENT_TIMESTAMP - INTERVAL '9 days', CURRENT_TIMESTAMP - INTERVAL '9 days'),
('271f2096-cf89-428c-8087-5647fdc99339', 'c35f34c3-337f-410b-b57a-e439a7ba969b', '高雄市鼓山區美術館路45號', '0912345678', 'credit_card', 'coupon', 1, 45000, 40490, CURRENT_TIMESTAMP - INTERVAL '8 days', CURRENT_TIMESTAMP - INTERVAL '8 days'),
('b020fdc5-5c7d-419d-b24f-fde477c82d27', '568ed618-7b23-4b88-a2fb-d519d1176a63', '台中市西區公益路321巷9號', '0987654321', 'credit_card', 'none', 1, 45000, NULL, CURRENT_TIMESTAMP - INTERVAL '7 days', CURRENT_TIMESTAMP - INTERVAL '7 days'),
('e3447913-9796-456b-a66b-dce3aafbbb8b', 'c3d1513b-b8f0-48de-b7c3-3a75485f8ae6', '台北市中山區南京東路3段123號', '0987654321', 'credit_card', 'coupon', 1, 98000, 83000, CURRENT_TIMESTAMP - INTERVAL '4 days', CURRENT_TIMESTAMP - INTERVAL '4 days'),
('14dcadc5-26be-4868-8b84-c6651b2452a5', '568ed618-7b23-4b88-a2fb-d519d1176a63', '台中市西區公益路321巷9號', '0987654321', 'atm', 'none', 1, 98000, NULL, CURRENT_TIMESTAMP - INTERVAL '3 days', CURRENT_TIMESTAMP - INTERVAL '3 days'),
('ffc9a14e-0f11-43ce-9b7a-588c52ca02dc', 'c35f34c3-337f-410b-b57a-e439a7ba969b', '高雄市鼓山區美術館路45號', '0912345678', 'credit_card', 'coupon', 1, 85000, 84700, CURRENT_TIMESTAMP - INTERVAL '30 days', CURRENT_TIMESTAMP - INTERVAL '30 days'),
('9fa3756a-2625-4c3e-8581-d44f032c5894', 'c3d1513b-b8f0-48de-b7c3-3a75485f8ae6', '台北市中山區南京東路3段123號', '0987654321', 'credit_card', 'point', 1, 8400, 8200, CURRENT_TIMESTAMP - INTERVAL '29 days', CURRENT_TIMESTAMP - INTERVAL '29 days'),
('991f0bb9-e8fd-47b4-9019-6fbd7952dbe1', 'c35f34c3-337f-410b-b57a-e439a7ba969b', '高雄市鼓山區美術館路45號', '0912345678', 'cvs', 'none', 1, 12600, NULL, CURRENT_TIMESTAMP - INTERVAL '28 days', CURRENT_TIMESTAMP - INTERVAL '28 days'),
('3a2ca85d-2384-40a7-b970-69821733277a', '568ed618-7b23-4b88-a2fb-d519d1176a63', '台中市西區公益路321巷9號', '0987654321', 'credit_card', 'point', 1, 30000, 29680, CURRENT_TIMESTAMP - INTERVAL '27 days', CURRENT_TIMESTAMP - INTERVAL '27 days'),
('c50b5a31-084a-4071-a1bc-ed84b2dfdf03', 'c3d1513b-b8f0-48de-b7c3-3a75485f8ae6', '台北市中山區南京東路3段123號', '0987654321', 'credit_card', 'none', 1, 19000, NULL, CURRENT_TIMESTAMP - INTERVAL '26 days', CURRENT_TIMESTAMP - INTERVAL '26 days'),
('5a8d9174-3da6-4cb7-b3f6-ceb395dfba50', '568ed618-7b23-4b88-a2fb-d519d1176a63', '台中市西區公益路321巷9號', '0987654321', 'credit_card', 'none', 1, 9500, NULL, CURRENT_TIMESTAMP - INTERVAL '25 days', CURRENT_TIMESTAMP - INTERVAL '25 days'),
('a1efba0e-62f7-4234-91ce-25eb8caa57ce', 'c35f34c3-337f-410b-b57a-e439a7ba969b', '高雄市鼓山區美術館路45號', '0912345678', 'credit_card', 'none', 1, 22000, NULL, CURRENT_TIMESTAMP - INTERVAL '24 days', CURRENT_TIMESTAMP - INTERVAL '24 days'),
('7650668e-16e8-4107-a63c-56e49805705a', 'c35f34c3-337f-410b-b57a-e439a7ba969b', '高雄市鼓山區美術館路45號', '0912345678', 'credit_card', 'point', 1, 18000, 17600, CURRENT_TIMESTAMP - INTERVAL '23 days', CURRENT_TIMESTAMP - INTERVAL '23 days'),
('229652ef-084a-411d-8564-614aefe78256', '568ed618-7b23-4b88-a2fb-d519d1176a63', '台中市西區公益路321巷9號', '0987654321', 'credit_card', 'none', 1, 9000, NULL, CURRENT_TIMESTAMP - INTERVAL '22 days', CURRENT_TIMESTAMP - INTERVAL '22 days'),
('75ae017f-9925-4728-98cc-f4cdf1e726f3', 'c3d1513b-b8f0-48de-b7c3-3a75485f8ae6', '台北市中山區南京東路3段123號', '0987654321', 'credit_card', 'none', 1, 17600, NULL, CURRENT_TIMESTAMP - INTERVAL '21 days', CURRENT_TIMESTAMP - INTERVAL '21 days'),
('69a683cb-c098-4461-87f2-7b1d3ed3dad8', 'c3d1513b-b8f0-48de-b7c3-3a75485f8ae6', NULL, NULL, NULL, NULL, -1, 72000, NULL, CURRENT_TIMESTAMP - INTERVAL '20 days', CURRENT_TIMESTAMP - INTERVAL '20 days'),
('9e639d53-e3a4-440a-ad9e-3b9512081540', 'c35f34c3-337f-410b-b57a-e439a7ba969b', '高雄市鼓山區美術館路45號', '0912345678', 'atm', 'none', 0, 15000, NULL, CURRENT_TIMESTAMP - INTERVAL '19 days', CURRENT_TIMESTAMP - INTERVAL '19 days'),
('72bb7891-162f-4139-8792-656452d1532b', '568ed618-7b23-4b88-a2fb-d519d1176a63', '台中市西區公益路321巷9號', '0987654321', 'credit_card', 'none', 2, 85000, NULL, CURRENT_TIMESTAMP - INTERVAL '18 days', CURRENT_TIMESTAMP - INTERVAL '18 days'),
('e4802aa7-13ba-46da-840f-5b08d623fb8d', '568ed618-7b23-4b88-a2fb-d519d1176a63', '台中市西區公益路321巷9號', '0987654321', 'credit_card', 'none', 3, 22000, NULL, CURRENT_TIMESTAMP - INTERVAL '17 days', CURRENT_TIMESTAMP - INTERVAL '17 days'),
('523421dc-62eb-4c8a-866c-0a68d503ffcb', 'c3d1513b-b8f0-48de-b7c3-3a75485f8ae6', '台北市中山區南京東路3段123號', '0987654321', 'cvs', 'none', 4, 85000, NULL, CURRENT_TIMESTAMP - INTERVAL '16 days', CURRENT_TIMESTAMP - INTERVAL '16 days')
ON CONFLICT DO NOTHING;

---- 18. 訂單細項資料 "order_item"
INSERT INTO order_item (order_item_id, order_id, tour_id, total_price, discount_price, payment_status, quantity, start_date, end_date, room_type, created_at, updated_at) VALUES
('58f91973-bccd-47fc-8385-111268543ba2', 'b294a0bd-a29b-40c9-8228-721c0e31899e', 'c35e011b-ffe4-48ea-8511-9f27ef0d5d69', 45000, 40500, 1, 1, (TIMESTAMP '2025-12-01 00:00:00' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), (TIMESTAMP '2025-12-05 23:59:59' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), NULL, CURRENT_TIMESTAMP - INTERVAL '9 days', CURRENT_TIMESTAMP - INTERVAL '9 days'),
('74250bad-0935-454a-9a5e-7778b0c3d49f', '271f2096-cf89-428c-8087-5647fdc99339', 'c35e011b-ffe4-48ea-8511-9f27ef0d5d69', 45000, 40500, 1, 1, (TIMESTAMP '2025-12-01 00:00:00' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), (TIMESTAMP '2025-12-05 23:59:59' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), NULL, CURRENT_TIMESTAMP - INTERVAL '8 days', CURRENT_TIMESTAMP - INTERVAL '8 days'),
('4c31ffc2-b421-4b86-b380-e106354e6cd6', 'b020fdc5-5c7d-419d-b24f-fde477c82d27', 'c35e011b-ffe4-48ea-8511-9f27ef0d5d69', 45000, 40500, 1, 1, (TIMESTAMP '2025-12-01 00:00:00' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), (TIMESTAMP '2025-12-05 23:59:59' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), NULL, CURRENT_TIMESTAMP - INTERVAL '7 days', CURRENT_TIMESTAMP - INTERVAL '7 days'),
('befaa739-14d4-47d6-bbfd-4f08facafff1', 'e3447913-9796-456b-a66b-dce3aafbbb8b', '9fd27d62-39ba-4b57-8015-6cfc47bb0a52', 98000, 83300, 1, 1, (TIMESTAMP '2025-11-10 00:00:00' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), (TIMESTAMP '2025-11-15 23:59:59' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), NULL, CURRENT_TIMESTAMP - INTERVAL '4 days', CURRENT_TIMESTAMP - INTERVAL '4 days'),
('da29b386-b399-4e2e-a473-3967808057d8', '14dcadc5-26be-4868-8b84-c6651b2452a5', '9fd27d62-39ba-4b57-8015-6cfc47bb0a52', 98000, 83300, 1, 1, (TIMESTAMP '2025-11-10 00:00:00' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), (TIMESTAMP '2025-11-15 23:59:59' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), NULL, CURRENT_TIMESTAMP - INTERVAL '3 days', CURRENT_TIMESTAMP - INTERVAL '3 days'),
('6b1a2f2a-5920-4ea0-9c00-ad73f907b7b2', 'ffc9a14e-0f11-43ce-9b7a-588c52ca02dc', 'f7cdc48d-7443-4b5b-b12a-31a5fa287dd2', 85000, NULL, 1, 1, (TIMESTAMP '2025-11-05 00:00:00' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), (TIMESTAMP '2025-11-15 23:59:59' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), NULL, CURRENT_TIMESTAMP - INTERVAL '30 days', CURRENT_TIMESTAMP - INTERVAL '30 days'),
('59359423-b6e2-4a5c-92b6-c14610fd132d', '9fa3756a-2625-4c3e-8581-d44f032c5894', 'b6e2735c-db96-4497-a197-e56c52e2aa64', 8400, NULL, 1, 2, (TIMESTAMP '2025-06-19' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), NULL, NULL, CURRENT_TIMESTAMP - INTERVAL '29 days', CURRENT_TIMESTAMP - INTERVAL '29 days'),
('ffb27682-d280-4387-90ad-35e0e312381a', '991f0bb9-e8fd-47b4-9019-6fbd7952dbe1', 'b6e2735c-db96-4497-a197-e56c52e2aa64', 12600, NULL, 1, 3, (TIMESTAMP '2025-06-19' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), NULL, NULL, CURRENT_TIMESTAMP - INTERVAL '28 days', CURRENT_TIMESTAMP - INTERVAL '28 days'),
('d08ff861-d52f-4846-aee0-f1a76a1594b4', '3a2ca85d-2384-40a7-b970-69821733277a', '85f6fdfb-7a95-4379-8fd3-568b0810b46e', 30000, NULL, 1, 2, (TIMESTAMP '2025-06-19' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), NULL, NULL, CURRENT_TIMESTAMP - INTERVAL '27 days', CURRENT_TIMESTAMP - INTERVAL '27 days'),
('36d81ec3-dc39-457d-b1fc-69a5a18b5795', 'c50b5a31-084a-4071-a1bc-ed84b2dfdf03', '6045e5a7-50f4-4cfc-814a-bface065157f', 19000, NULL, 1, 2, (TIMESTAMP '2025-06-19' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), NULL, NULL, CURRENT_TIMESTAMP - INTERVAL '26 days', CURRENT_TIMESTAMP - INTERVAL '26 days'),
('87526e29-bb46-40eb-8710-e70b944028fe', '5a8d9174-3da6-4cb7-b3f6-ceb395dfba50', '6045e5a7-50f4-4cfc-814a-bface065157f', 9500, NULL, 1, 1, (TIMESTAMP '2025-06-19' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), NULL, NULL, CURRENT_TIMESTAMP - INTERVAL '25 days', CURRENT_TIMESTAMP - INTERVAL '25 days'),
('36c2bb92-ba7f-4159-8271-daff43511545', 'a1efba0e-62f7-4234-91ce-25eb8caa57ce', '57bfb290-092a-40c7-a68c-7b1a032cfe64', 22000, NULL, 1, 1, (TIMESTAMP '2025-06-19' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), NULL, NULL, CURRENT_TIMESTAMP - INTERVAL '24 days', CURRENT_TIMESTAMP - INTERVAL '24 days'),
('b69ab9ad-09de-4fe0-bcc4-5c1875ed7891', '7650668e-16e8-4107-a63c-56e49805705a', '1692beb1-be37-4a73-93e4-89d0adf1250c', 18000, NULL, 1, 2, (TIMESTAMP '2025-06-19' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), (TIMESTAMP '2025-06-21' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), '設計雙人房', CURRENT_TIMESTAMP - INTERVAL '23 days', CURRENT_TIMESTAMP - INTERVAL '23 days'),
('92652aec-e95e-46e5-aed5-0de97bd66d2c', '229652ef-084a-411d-8564-614aefe78256', '1692beb1-be37-4a73-93e4-89d0adf1250c', 9000, NULL, 1, 1, (TIMESTAMP '2025-06-19' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), (TIMESTAMP '2025-06-21' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), '設計雙人房', CURRENT_TIMESTAMP - INTERVAL '22 days', CURRENT_TIMESTAMP - INTERVAL '22 days'),
('fa0e554d-bf1c-40cc-940a-d92baeb85c41', '75ae017f-9925-4728-98cc-f4cdf1e726f3', '144d34ec-2c8c-491f-9f7c-def1351e49d6', 17600, NULL, 1, 2, (TIMESTAMP '2025-06-19' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), (TIMESTAMP '2025-06-21' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), '海景雙人房', CURRENT_TIMESTAMP - INTERVAL '21 days', CURRENT_TIMESTAMP - INTERVAL '21 days'),
('7d853da0-3b46-4572-adac-417d355c63ab', '69a683cb-c098-4461-87f2-7b1d3ed3dad8', '8c74c63e-933e-4623-aa4c-f3814db9c6c2', 72000, NULL, -1, 1, (TIMESTAMP '2025-10-15 00:00:00' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), (TIMESTAMP '2025-10-22 23:59:59' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), NULL, CURRENT_TIMESTAMP - INTERVAL '20 days', CURRENT_TIMESTAMP - INTERVAL '20 days'),
('2624af5f-345f-4cb5-9fff-40a1a967717d', '9e639d53-e3a4-440a-ad9e-3b9512081540', '85f6fdfb-7a95-4379-8fd3-568b0810b46e', 15000, NULL, 0, 1, (TIMESTAMP '2025-06-19' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), NULL, NULL, CURRENT_TIMESTAMP - INTERVAL '19 days', CURRENT_TIMESTAMP - INTERVAL '19 days'),
('30be478c-7f47-4762-8b14-49ffe33c70ea', '72bb7891-162f-4139-8792-656452d1532b', 'f7cdc48d-7443-4b5b-b12a-31a5fa287dd2', 85000, NULL, 2, 1, (TIMESTAMP '2025-11-05 00:00:00' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), (TIMESTAMP '2025-11-15 23:59:59' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), NULL, CURRENT_TIMESTAMP - INTERVAL '18 days', CURRENT_TIMESTAMP - INTERVAL '18 days'),
('7968a1cc-3ac5-4ccf-ac9c-8b60afa31060', 'e4802aa7-13ba-46da-840f-5b08d623fb8d', '57bfb290-092a-40c7-a68c-7b1a032cfe64', 22000, NULL, 3, 1, (TIMESTAMP '2025-06-19' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), NULL, NULL, CURRENT_TIMESTAMP - INTERVAL '17 days', CURRENT_TIMESTAMP - INTERVAL '17 days'),
('f5ae4782-f21a-4b85-b138-7b94b542acbb', '523421dc-62eb-4c8a-866c-0a68d503ffcb', 'f7cdc48d-7443-4b5b-b12a-31a5fa287dd2', 85000, NULL, 4, 1, (TIMESTAMP '2025-11-05 00:00:00' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), (TIMESTAMP '2025-11-15 23:59:59' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), NULL, CURRENT_TIMESTAMP - INTERVAL '16 days', CURRENT_TIMESTAMP - INTERVAL '16 days')
ON CONFLICT DO NOTHING;

---- 19. 付款紀錄資料 "payment"
INSERT INTO payment (payment_id, user_id, order_id, address, phone, payment_method, payment_status, discount_price, return_data, return_time, result_info, result_time) VALUES
('d6c1c3cc-f053-43c1-b3ad-8f4ed98049d1', 'c3d1513b-b8f0-48de-b7c3-3a75485f8ae6', 'b294a0bd-a29b-40c9-8228-721c0e31899e', '台北市中山區南京東路3段123號', '0987654321', 'credit_card', 1, NULL, '{"Status":"SUCCESS","Result":{"MerchantOrderNo":"b294a0bd-a29b-40c9-8228-721c0e31899e","PaymentType":"credit_card","Message":"付款成功"}}', CURRENT_TIMESTAMP, '付款成功', CURRENT_TIMESTAMP),
('49384278-8601-48b8-bfd0-6522fef40c69', 'c35f34c3-337f-410b-b57a-e439a7ba969b', '271f2096-cf89-428c-8087-5647fdc99339', '高雄市鼓山區美術館路45號', '0912345678', 'credit_card', 1, 40490, '{"Status":"SUCCESS","Result":{"MerchantOrderNo":"271f2096-cf89-428c-8087-5647fdc99339","PaymentType":"credit_card","Message":"付款成功"}}', CURRENT_TIMESTAMP, '付款成功', CURRENT_TIMESTAMP),
('d43ee26a-d43c-4037-a2ad-f323fa494bde', '568ed618-7b23-4b88-a2fb-d519d1176a63', 'b020fdc5-5c7d-419d-b24f-fde477c82d27', '台中市西區公益路321巷9號', '0987654321', 'credit_card', 1, NULL, '{"Status":"SUCCESS","Result":{"MerchantOrderNo":"b020fdc5-5c7d-419d-b24f-fde477c82d27","PaymentType":"credit_card","Message":"付款成功"}}', CURRENT_TIMESTAMP, '付款成功', CURRENT_TIMESTAMP),
('73293871-9662-48ab-ba11-cfde7d6daf01', 'c3d1513b-b8f0-48de-b7c3-3a75485f8ae6', 'e3447913-9796-456b-a66b-dce3aafbbb8b', '台北市中山區南京東路3段123號', '0987654321', 'credit_card', 1, 83000, '{"Status":"SUCCESS","Result":{"MerchantOrderNo":"e3447913-9796-456b-a66b-dce3aafbbb8b","PaymentType":"credit_card","Message":"付款成功"}}', CURRENT_TIMESTAMP, '付款成功', CURRENT_TIMESTAMP),
('8d56d512-6076-4323-8d28-26f3b9e4399a', '568ed618-7b23-4b88-a2fb-d519d1176a63', '14dcadc5-26be-4868-8b84-c6651b2452a5', '台中市西區公益路321巷9號', '0987654321', 'atm', 1, NULL, '{"Status":"SUCCESS","Result":{"MerchantOrderNo":"14dcadc5-26be-4868-8b84-c6651b2452a5","PaymentType":"atm","Message":"付款成功"}}', CURRENT_TIMESTAMP, '付款成功', CURRENT_TIMESTAMP),
('b06cdd7d-5e55-453a-8ee2-175a651a0bb3', 'c35f34c3-337f-410b-b57a-e439a7ba969b', 'ffc9a14e-0f11-43ce-9b7a-588c52ca02dc', '高雄市鼓山區美術館路45號', '0912345678', 'credit_card', 1, 84700, '{"Status":"SUCCESS","Result":{"MerchantOrderNo":"ffc9a14e-0f11-43ce-9b7a-588c52ca02dc","PaymentType":"credit_card","Message":"付款成功"}}', CURRENT_TIMESTAMP, '付款成功', CURRENT_TIMESTAMP),
('dfab36ad-cd7e-4a49-b93c-f53487ef8eef', 'c3d1513b-b8f0-48de-b7c3-3a75485f8ae6', '9fa3756a-2625-4c3e-8581-d44f032c5894', '台北市中山區南京東路3段123號', '0987654321', 'credit_card', 1, 8200, '{"Status":"SUCCESS","Result":{"MerchantOrderNo":"9fa3756a-2625-4c3e-8581-d44f032c5894","PaymentType":"credit_card","Message":"付款成功"}}', CURRENT_TIMESTAMP, '付款成功', CURRENT_TIMESTAMP),
('6e45d3da-e0e3-486f-a1c7-7fcd341181a9', 'c35f34c3-337f-410b-b57a-e439a7ba969b', '991f0bb9-e8fd-47b4-9019-6fbd7952dbe1', '高雄市鼓山區美術館路45號', '0912345678', 'cvs', 1, NULL, '{"Status":"SUCCESS","Result":{"MerchantOrderNo":"991f0bb9-e8fd-47b4-9019-6fbd7952dbe1","PaymentType":"cvs","Message":"付款成功"}}', CURRENT_TIMESTAMP, '付款成功', CURRENT_TIMESTAMP),
('0bfc278f-fd6d-4a53-ba1a-bfabac99b0e8', '568ed618-7b23-4b88-a2fb-d519d1176a63', '3a2ca85d-2384-40a7-b970-69821733277a', '台中市西區公益路321巷9號', '0987654321', 'credit_card', 1, 29680, '{"Status":"SUCCESS","Result":{"MerchantOrderNo":"3a2ca85d-2384-40a7-b970-69821733277a","PaymentType":"credit_card","Message":"付款成功"}}', CURRENT_TIMESTAMP, '付款成功', CURRENT_TIMESTAMP),
('b7d1af2b-50da-4cb8-b36f-2b7b73671ee4', 'c3d1513b-b8f0-48de-b7c3-3a75485f8ae6', 'c50b5a31-084a-4071-a1bc-ed84b2dfdf03', '台北市中山區南京東路3段123號', '0987654321', 'credit_card', 1, NULL, '{"Status":"SUCCESS","Result":{"MerchantOrderNo":"c50b5a31-084a-4071-a1bc-ed84b2dfdf03","PaymentType":"credit_card","Message":"付款成功"}}', CURRENT_TIMESTAMP, '付款成功', CURRENT_TIMESTAMP),
('bf435431-03f4-48f8-9211-215757c2914d', '568ed618-7b23-4b88-a2fb-d519d1176a63', '5a8d9174-3da6-4cb7-b3f6-ceb395dfba50', '台中市西區公益路321巷9號', '0987654321', 'credit_card', 1, NULL, '{"Status":"SUCCESS","Result":{"MerchantOrderNo":"5a8d9174-3da6-4cb7-b3f6-ceb395dfba50","PaymentType":"credit_card","Message":"付款成功"}}', CURRENT_TIMESTAMP, '付款成功', CURRENT_TIMESTAMP),
('56c71f6d-199f-4fcc-93d6-79ce885b5f66', 'c35f34c3-337f-410b-b57a-e439a7ba969b', 'a1efba0e-62f7-4234-91ce-25eb8caa57ce', '高雄市鼓山區美術館路45號', '0912345678', 'credit_card', 1, NULL, '{"Status":"SUCCESS","Result":{"MerchantOrderNo":"a1efba0e-62f7-4234-91ce-25eb8caa57ce","PaymentType":"credit_card","Message":"付款成功"}}', CURRENT_TIMESTAMP, '付款成功', CURRENT_TIMESTAMP),
('12c654e8-840b-481d-9c78-e5f833d313de', 'c35f34c3-337f-410b-b57a-e439a7ba969b', '7650668e-16e8-4107-a63c-56e49805705a', '高雄市鼓山區美術館路45號', '0912345678', 'credit_card', 1, 17600, '{"Status":"SUCCESS","Result":{"MerchantOrderNo":"7650668e-16e8-4107-a63c-56e49805705a","PaymentType":"credit_card","Message":"付款成功"}}', CURRENT_TIMESTAMP, '付款成功', CURRENT_TIMESTAMP),
('78c1ad39-93c2-4dee-90fe-3e8ee6e63309', '568ed618-7b23-4b88-a2fb-d519d1176a63', '229652ef-084a-411d-8564-614aefe78256', '台中市西區公益路321巷9號', '0987654321', 'credit_card', 1, NULL, '{"Status":"SUCCESS","Result":{"MerchantOrderNo":"229652ef-084a-411d-8564-614aefe78256","PaymentType":"credit_card","Message":"付款成功"}}', CURRENT_TIMESTAMP, '付款成功', CURRENT_TIMESTAMP),
('a6dc1c7d-0a54-4609-8820-55c65f95fa31', 'c3d1513b-b8f0-48de-b7c3-3a75485f8ae6', '75ae017f-9925-4728-98cc-f4cdf1e726f3', '台北市中山區南京東路3段123號', '0987654321', 'credit_card', 1, NULL, '{"Status":"SUCCESS","Result":{"MerchantOrderNo":"75ae017f-9925-4728-98cc-f4cdf1e726f3","PaymentType":"credit_card","Message":"付款成功"}}', CURRENT_TIMESTAMP, '付款成功', CURRENT_TIMESTAMP)
ON CONFLICT DO NOTHING;

---- 20. 評論資料 "review"
INSERT INTO "review" (review_id, user_id, tour_id, type, hashtag, rating, content, created_at, updated_at) VALUES
('f7bb59cb-7083-4f13-970c-be042318f601', 'c3d1513b-b8f0-48de-b7c3-3a75485f8ae6', NULL, 'web', '#操作直覺', 5, '整個網站設計非常友善，喜歡！', CURRENT_TIMESTAMP - INTERVAL '5 days', CURRENT_TIMESTAMP - INTERVAL '5 days'),
('b7176b76-f9fc-4d7b-b1a6-9abeb73e51b9', 'c35f34c3-337f-410b-b57a-e439a7ba969b', NULL, 'web', '#速度很快', 4, '下單流程簡單又快速，推薦。', CURRENT_TIMESTAMP - INTERVAL '4 days', CURRENT_TIMESTAMP - INTERVAL '4 days'),
('7ea6feb4-833b-4dcf-90ed-e6e857067286', '568ed618-7b23-4b88-a2fb-d519d1176a63', 'f7cdc48d-7443-4b5b-b12a-31a5fa287dd2', 'travel', NULL, 5, '北海道行程安排完美，超值！', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('27bdee51-50bf-4131-a14c-e4755f151c8f', 'c3d1513b-b8f0-48de-b7c3-3a75485f8ae6', 'c35e011b-ffe4-48ea-8511-9f27ef0d5d69', 'travel', NULL, 4, '巴黎巡禮浪漫又美麗！', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('8238d1b5-b73d-45d5-be9d-97ba2fa7376c', 'c35f34c3-337f-410b-b57a-e439a7ba969b', '9fd27d62-39ba-4b57-8015-6cfc47bb0a52', 'hotel', NULL, 5, '飯店地點方便，乾淨舒適。', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('59674d9d-3c5e-4aba-8e5d-b5dc4da4154b', '568ed618-7b23-4b88-a2fb-d519d1176a63', '85f6fdfb-7a95-4379-8fd3-568b0810b46e', 'hotel', NULL, 4, '設施不錯但早餐普通。', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('27826ed1-095c-421b-b518-5a3446331755', 'c3d1513b-b8f0-48de-b7c3-3a75485f8ae6', '57bfb290-092a-40c7-a68c-7b1a032cfe64', 'food', NULL, 5, '曼谷美食超級好吃，值得一試！', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('2919e128-be3d-4eaa-b117-0fc4623277fa', 'c35f34c3-337f-410b-b57a-e439a7ba969b', '1692beb1-be37-4a73-93e4-89d0adf1250c', 'food', NULL, 3, '有些小吃偏油但整體好吃。', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('698d530c-c7b4-4599-8c5b-853d01bf51f6', '568ed618-7b23-4b88-a2fb-d519d1176a63', '8c74c63e-933e-4623-aa4c-f3814db9c6c2', 'spot', NULL, 5, '景色壯觀，很值得一遊！', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('c0285ca0-d14e-424f-b1f1-1625016b3157', 'c3d1513b-b8f0-48de-b7c3-3a75485f8ae6', '6045e5a7-50f4-4cfc-814a-bface065157f', 'spot', NULL, 4, '景點人潮多但風景超美。', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('06fa38b7-e4af-4bac-8297-7bb7a7435783', '568ed618-7b23-4b88-a2fb-d519d1176a63', NULL, 'web', '#介面清爽', 5, '行程搜尋很好用，收藏功能也很方便。', CURRENT_TIMESTAMP - INTERVAL '3 days', CURRENT_TIMESTAMP - INTERVAL '3 days'),
('4fdb643b-0725-456f-8d77-fb75648da2a3', 'c3d1513b-b8f0-48de-b7c3-3a75485f8ae6', NULL, 'web', '#資訊完整', 4, '商品頁的資訊很完整，比價很省時間。', CURRENT_TIMESTAMP - INTERVAL '2 days', CURRENT_TIMESTAMP - INTERVAL '2 days'),
('fb04b5e8-5520-4f57-9496-b2a8363c3208', 'c35f34c3-337f-410b-b57a-e439a7ba969b', NULL, 'web', '#客服親切', 5, '訂單有問題時客服回覆很快。', CURRENT_TIMESTAMP - INTERVAL '1 days', CURRENT_TIMESTAMP - INTERVAL '1 days')
ON CONFLICT DO NOTHING;

---- 21. 隱藏玩法資料 "hidden_play"
INSERT INTO "hidden_play" (hidden_play_id, user_id, tour_id, title, content, share_url, created_at, updated_at) VALUES
('5217228d-5d5e-44a9-8d50-2ab331a873f2', 'c3d1513b-b8f0-48de-b7c3-3a75485f8ae6', 'f7cdc48d-7443-4b5b-b12a-31a5fa287dd2', '北海道隱藏雪景', '小巷裡的冰雕展超夢幻，遊客很少！', 'http://localhost:3000/uploads/seed/hidden.svg', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('8aef226a-9982-4384-a297-9f58e6455300', 'c35f34c3-337f-410b-b57a-e439a7ba969b', 'c35e011b-ffe4-48ea-8511-9f27ef0d5d69', '巴黎秘境咖啡廳', '塞納河旁的小咖啡廳，超有文青感。', 'http://localhost:3000/uploads/seed/hidden.svg', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('4fa2d57a-f9fe-4af7-aa8f-fa90030ab716', '568ed618-7b23-4b88-a2fb-d519d1176a63', '9fd27d62-39ba-4b57-8015-6cfc47bb0a52', '隱藏版清邁夜市', '本地人推薦的夜市小吃，便宜又好吃。', 'http://localhost:3000/uploads/seed/hidden.svg', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('bb48ee7a-cca0-4fde-bf68-f5d9126c3e56', 'c3d1513b-b8f0-48de-b7c3-3a75485f8ae6', '85f6fdfb-7a95-4379-8fd3-568b0810b46e', '秘密海灘', '搭乘小船才能到達的超夢幻海灘。', 'http://localhost:3000/uploads/seed/hidden.svg', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('35dfb95a-558d-4a7f-8ae6-2ab41f84c6ea', 'c35f34c3-337f-410b-b57a-e439a7ba969b', '57bfb290-092a-40c7-a68c-7b1a032cfe64', '曼谷隱藏美食街', '巷弄內隱藏的米其林推薦小吃。', 'http://localhost:3000/uploads/seed/hidden.svg', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('f6ad3ab6-2aae-45a4-8b9e-877952bdaa38', '568ed618-7b23-4b88-a2fb-d519d1176a63', '1692beb1-be37-4a73-93e4-89d0adf1250c', '紐約市秘密書店', '藏身公園旁的獨立書店，超有味道。', 'http://localhost:3000/uploads/seed/hidden.svg', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
ON CONFLICT DO NOTHING;

---- 22. 自動設定資料 "auto_setting"
INSERT INTO "auto_setting" (auto_setting_id, user_id, early_notify, flexible_notify, country, region, price, created_at, updated_at) VALUES
('d47d7d56-46dd-48ff-bf22-afcb3f46d2a9', 'c3d1513b-b8f0-48de-b7c3-3a75485f8ae6', 0, 1, 'Japan', 'Tokyo', 1200.5, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('deb6ca0e-0bac-44fb-afcc-6102bd05b317', 'c35f34c3-337f-410b-b57a-e439a7ba969b', 0, 0, NULL, NULL, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('f48d33c9-bcbb-41a7-b03a-577620e69e0c', '568ed618-7b23-4b88-a2fb-d519d1176a63', 1, 1, 'France', 'Paris', 1850.75, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('8eb334ed-2c98-4cd0-a7e5-c88c695ad14f', 'c3d1513b-b8f0-48de-b7c3-3a75485f8ae6', 1, 0, NULL, NULL, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
ON CONFLICT DO NOTHING;

---- 23. 使用者收藏旅遊商品 "favorite"
INSERT INTO "favorite" (favorite_id, user_id, tour_id, created_at, updated_at) VALUES
('0b8b065d-cd65-4458-b500-53354769aa7b', 'c3d1513b-b8f0-48de-b7c3-3a75485f8ae6', 'f7cdc48d-7443-4b5b-b12a-31a5fa287dd2', CURRENT_TIMESTAMP - INTERVAL '10 days', CURRENT_TIMESTAMP - INTERVAL '10 days'),
('c6211142-60d5-4807-aaa3-6ee7d9aae057', 'c35f34c3-337f-410b-b57a-e439a7ba969b', 'c35e011b-ffe4-48ea-8511-9f27ef0d5d69', CURRENT_TIMESTAMP - INTERVAL '9 days', CURRENT_TIMESTAMP - INTERVAL '9 days'),
('dde29f63-9d68-4cd3-8640-a8d18717df6a', '568ed618-7b23-4b88-a2fb-d519d1176a63', '9fd27d62-39ba-4b57-8015-6cfc47bb0a52', CURRENT_TIMESTAMP - INTERVAL '8 days', CURRENT_TIMESTAMP - INTERVAL '8 days'),
('fa6cc00d-d80e-437f-bbee-5f1089e9ee74', 'c3d1513b-b8f0-48de-b7c3-3a75485f8ae6', '9fd27d62-39ba-4b57-8015-6cfc47bb0a52', CURRENT_TIMESTAMP - INTERVAL '7 days', CURRENT_TIMESTAMP - INTERVAL '7 days'),
('f435595a-41d9-4320-a41d-deea24617c5d', 'c3d1513b-b8f0-48de-b7c3-3a75485f8ae6', '85f6fdfb-7a95-4379-8fd3-568b0810b46e', CURRENT_TIMESTAMP - INTERVAL '3 days', CURRENT_TIMESTAMP - INTERVAL '3 days'),
('74cabd97-b303-4e4c-bde9-c68e3cb61e09', 'c35f34c3-337f-410b-b57a-e439a7ba969b', '57bfb290-092a-40c7-a68c-7b1a032cfe64', CURRENT_TIMESTAMP - INTERVAL '5 days', CURRENT_TIMESTAMP - INTERVAL '5 days'),
('a0b84500-9e6f-43fa-905c-10204e289cbd', '568ed618-7b23-4b88-a2fb-d519d1176a63', '1692beb1-be37-4a73-93e4-89d0adf1250c', CURRENT_TIMESTAMP - INTERVAL '4 days', CURRENT_TIMESTAMP - INTERVAL '4 days'),
('e0fc6ba0-b847-438c-aa29-c6fb57227dd2', 'c3d1513b-b8f0-48de-b7c3-3a75485f8ae6', 'c35e011b-ffe4-48ea-8511-9f27ef0d5d69', CURRENT_TIMESTAMP - INTERVAL '1 days', CURRENT_TIMESTAMP - INTERVAL '1 days'),
('34323c87-0a97-49b4-b79e-21257689197d', 'c35f34c3-337f-410b-b57a-e439a7ba969b', '9fd27d62-39ba-4b57-8015-6cfc47bb0a52', CURRENT_TIMESTAMP - INTERVAL '2 days', CURRENT_TIMESTAMP - INTERVAL '2 days')
ON CONFLICT DO NOTHING;

---- 24. 會員旅遊積分資料 "point_record"
INSERT INTO point_record (point_id, user_id, order_id, type, point) VALUES
('6508e89a-3909-4f01-b3a6-9448742270b4', 'c3d1513b-b8f0-48de-b7c3-3a75485f8ae6', 'b294a0bd-a29b-40c9-8228-721c0e31899e', '新增', 4050),
('e0224c2b-17d7-4607-819d-c2c9e4d6f82a', 'c35f34c3-337f-410b-b57a-e439a7ba969b', '271f2096-cf89-428c-8087-5647fdc99339', '新增', 4049),
('e9320070-7c73-450d-a609-3d5a4377b4e1', '568ed618-7b23-4b88-a2fb-d519d1176a63', 'b020fdc5-5c7d-419d-b24f-fde477c82d27', '新增', 4050),
('859854e8-67df-4ba6-9e44-d8f29e729e3f', 'c3d1513b-b8f0-48de-b7c3-3a75485f8ae6', 'e3447913-9796-456b-a66b-dce3aafbbb8b', '新增', 8300),
('c2e92131-bea7-4d6c-8aa8-0d22afd244f0', '568ed618-7b23-4b88-a2fb-d519d1176a63', '14dcadc5-26be-4868-8b84-c6651b2452a5', '新增', 8330),
('d05b5f14-dc9c-46bf-be61-d61fb2e36e23', 'c35f34c3-337f-410b-b57a-e439a7ba969b', 'ffc9a14e-0f11-43ce-9b7a-588c52ca02dc', '新增', 8470),
('c98d3462-24af-4843-91bb-4aab3450403c', 'c3d1513b-b8f0-48de-b7c3-3a75485f8ae6', '9fa3756a-2625-4c3e-8581-d44f032c5894', '新增', 820),
('a7535753-3071-47e3-aa5e-10517e57f337', 'c35f34c3-337f-410b-b57a-e439a7ba969b', '991f0bb9-e8fd-47b4-9019-6fbd7952dbe1', '新增', 1260),
('3e4d7e77-c3a4-4fcd-8e85-97368f2b7dcb', '568ed618-7b23-4b88-a2fb-d519d1176a63', '3a2ca85d-2384-40a7-b970-69821733277a', '新增', 2968),
('10fa2f28-7dd3-461d-b107-d975b5a91afa', 'c3d1513b-b8f0-48de-b7c3-3a75485f8ae6', 'c50b5a31-084a-4071-a1bc-ed84b2dfdf03', '新增', 1900),
('7d0617b9-2393-4d77-bd15-e0fe12afedfb', '568ed618-7b23-4b88-a2fb-d519d1176a63', '5a8d9174-3da6-4cb7-b3f6-ceb395dfba50', '新增', 950),
('883cdeba-5f5e-4312-b563-710a5be44c77', 'c35f34c3-337f-410b-b57a-e439a7ba969b', 'a1efba0e-62f7-4234-91ce-25eb8caa57ce', '新增', 2200),
('a1aac1f9-57cb-48a0-8f30-09dbd6ecf264', 'c35f34c3-337f-410b-b57a-e439a7ba969b', '7650668e-16e8-4107-a63c-56e49805705a', '新增', 1760),
('63031429-2f23-4ca3-a5f6-a0204a8416b5', '568ed618-7b23-4b88-a2fb-d519d1176a63', '229652ef-084a-411d-8564-614aefe78256', '新增', 900),
('055a5db4-342e-43fa-90ef-bf5cfec262ab', 'c3d1513b-b8f0-48de-b7c3-3a75485f8ae6', '75ae017f-9925-4728-98cc-f4cdf1e726f3', '新增', 1760),
('88d8e7b9-a3f8-4fb9-9f72-58e1d30d7a7a', 'c3d1513b-b8f0-48de-b7c3-3a75485f8ae6', '9fa3756a-2625-4c3e-8581-d44f032c5894', '減少', -250),
('b0c81505-8445-4b8b-8c14-380a0877e4ae', '568ed618-7b23-4b88-a2fb-d519d1176a63', '3a2ca85d-2384-40a7-b970-69821733277a', '減少', -400),
('05f6d9f8-4057-405d-806a-64943ae8411b', 'c35f34c3-337f-410b-b57a-e439a7ba969b', '7650668e-16e8-4107-a63c-56e49805705a', '減少', -500)
ON CONFLICT DO NOTHING;

---- 25. 優惠卷與使用者綁定的資料 "user_coupon"
INSERT INTO "user_coupon" (user_coupon_id, user_id, order_id, coupon_id, status) VALUES
('fa5c98e6-1609-4bb0-9187-ae9a199468f9', 'c35f34c3-337f-410b-b57a-e439a7ba969b', '271f2096-cf89-428c-8087-5647fdc99339', 'dffebeb5-1a73-426f-8c3d-9b2a8f74108f', 1),
('f442cdc9-8c1e-4209-b044-398bcac594dc', '568ed618-7b23-4b88-a2fb-d519d1176a63', NULL, 'dffebeb5-1a73-426f-8c3d-9b2a8f74108f', 0),
('1a01b727-6991-453f-b433-1e81fb85f8cd', 'c35f34c3-337f-410b-b57a-e439a7ba969b', 'ffc9a14e-0f11-43ce-9b7a-588c52ca02dc', '7ab87d9e-8ff0-42ad-8252-939d1d80e21b', 1),
('b6846c8a-7d10-4d3f-84d9-eb583fa20fb2', 'c3d1513b-b8f0-48de-b7c3-3a75485f8ae6', 'e3447913-9796-456b-a66b-dce3aafbbb8b', '7ab87d9e-8ff0-42ad-8252-939d1d80e21b', 1)
ON CONFLICT DO NOTHING;
