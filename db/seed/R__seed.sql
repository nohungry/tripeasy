-- 本檔由 db/seed-build/build_seed.py 產生，請勿手動修改；要改請改腳本後重新產生。
-- 來源：db/seed-build/tripeasy_fakedata.sql
-- 只在本機與展示環境載入（compose 的 Flyway -locations 加上 db/seed），正式環境不載入。
-- 每個 INSERT 都是 ON CONFLICT DO NOTHING：重跑時既有的資料不會被更新。
-- 改了既有資料列的內容，要 docker compose down -v 重建 DB 才看得到。

/* ------------------ 產生假資料 -----------------------  */

---- 1. 會員基本資料 "user"
INSERT INTO "user" (
    user_id, name, email, role, password, login_attempts, locked_datetime, avatar_url, 
    preference1, preference2, preference3, login_method, created_at, updated_at
) VALUES
(
    'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
    'Alice Wang',
    'alice@example.com',
    'User',
    '$2b$10$9Bd0v0X7eLfhzEL5BC8pROe7OWUfOq4rFDMi.8K/Gg7prMuyn8OKi', 
    0,
    NULL,
    'http://localhost:3000/uploads/seed/avatar.svg',
    1,
    2,
    3,
    1,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
),
(
    'b2c3d4e5-f678-90ab-cdef-234567890abc',
    'Bob Chen',
    'bob@example.com',
    'admin',
    '$2b$10$9Bd0v0X7eLfhzEL5BC8pROe7OWUfOq4rFDMi.8K/Gg7prMuyn8OKi',
    1,
    NULL,
    'http://localhost:3000/uploads/seed/avatar.svg',
    2,
    1,
    3,
    2,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
),
(
    'c3d4e5f6-7890-abcd-ef12-34567890abcd',
    'Carol Lin',
    'carol@example.com',
    'User',
    '$2b$10$9Bd0v0X7eLfhzEL5BC8pROe7OWUfOq4rFDMi.8K/Gg7prMuyn8OKi',
    NULL,
    NULL,
    NULL,
    3,
    2,
    1,
    3,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
)
ON CONFLICT DO NOTHING;

---- 2. 會員第三方登入資料 "socialLogin"
INSERT INTO "socialLogin" (
    login_id, user_id, provider_method, provider_id, provider_token, created_at, updated_at
) VALUES
(
    'a1111111-b222-c333-d444-e55555555555',
    'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
    'google',
    'google_1234567890',
    'ya29.a0AfH6SMAExampleGoogleToken',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
),
(
    'b1111111-c222-d333-e444-f55555555555',
    'b2c3d4e5-f678-90ab-cdef-234567890abc',
    'facebook',
    'facebook_9876543210',
    'EAAGm0PX4ZCpsBADExampleFacebookToken',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
),
(
    'c1111111-d222-e333-f444-a55555555555',
    'c3d4e5f6-7890-abcd-ef12-34567890abcd',
    'apple',
    'apple_1122334455',
    'd6bbf92f9c3eExampleAppleToken',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
)
ON CONFLICT DO NOTHING;

---- 3. 會員等級資料 "user_level"
INSERT INTO "user_level" (
    level_id, user_id, level, name, badge_url, travel_point, benefits, created_at, updated_at
) VALUES
(
    'd4e5f678-90ab-cdef-1234-567890abcdef',
    'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
    'Level 3',
    'Explorer',
    'http://localhost:3000/uploads/seed/badge.svg',
    1500,
    'Free airport lounge access; 10% discount on tours',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
),
(
    'e5f67890-abcd-ef12-3456-7890abcdef12',
    'b2c3d4e5-f678-90ab-cdef-234567890abc',
    'Level 5',
    'Adventure Master',
    'http://localhost:3000/uploads/seed/badge.svg',
    3000,
    'VIP travel concierge; Free travel insurance',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
),
(
    'f67890ab-cdef-1234-5678-90abcdef1234',
    'c3d4e5f6-7890-abcd-ef12-34567890abcd',
    'Level 2',
    'Rookie Traveler',
    'http://localhost:3000/uploads/seed/badge.svg',
    800,
    'Priority customer support; Welcome gift',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
)
ON CONFLICT DO NOTHING;

---- 4. 優惠卷資料 "coupon"
INSERT INTO "coupon" (
    coupon_id, code, discount, description, expire_date, created_at, updated_at
) VALUES
(
    '11111111-aaaa-bbbb-cccc-111111111111',
    'WELCOME100',
    100.0,
    '首次註冊禮，折抵新台幣 100 元',
    (TIMESTAMP '2025-12-31 23:59:59' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'),
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
),
(
    '22222222-bbbb-cccc-dddd-222222222222',
    'SUMMER50',
    50.0,
    '夏日旅遊季，折抵新台幣 50 元',
    (TIMESTAMP '2025-08-31 23:59:59' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'),
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
),
(
    '33333333-cccc-dddd-eeee-333333333333',
    'TRAVEL10P',
    10.0,
    '旅遊商品 10% 折扣 (最高折抵 500 元)',
    (TIMESTAMP '2025-09-30 23:59:59' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'),
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
),
(
    '44444444-dddd-eeee-ffff-444444444444',
    'VIP300',
    300.0,
    '尊榮會員專屬，折抵新台幣 300 元',
    (TIMESTAMP '2025-12-31 23:59:59' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'),
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
),
(
    '55555555-eeee-ffff-aaaa-555555555555',
    'SPRING20',
    20.0,
    '春季限定，旅遊折抵新台幣 20 元',
    (TIMESTAMP '2025-05-31 23:59:59' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'),
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
)
ON CONFLICT DO NOTHING;

---- 5. 旅遊項目資料 "tour"
INSERT INTO "tour" (
    tour_id, type, item, status, title, slogan, tour_start_date, tour_end_date, days, price,
    country, region, address, google_map_url, calendar_url,
    preference1, preference2, preference3,
    notice, description,
    cover_image, img1, img1_desc, img2, img2_desc, img3, img3_desc,
    img4, img4_desc, img5, img5_desc, img6, img6_desc,
    created_at, updated_at
) VALUES
-- tourgroup: travel
(
    '11111111-aaaa-bbbb-cccc-111111111111',
    'tourgroup', 'travel', 1,
    '北海道雪景 5 日深度遊', '穿越銀白世界，體驗最美冬季',
    (TIMESTAMP '2025-12-01 00:00:00' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), (TIMESTAMP '2025-12-05 23:59:59' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), 5, 45000,
    'Japan', 'Hokkaido', '札幌市中央區南1條西2丁目',
    'https://goo.gl/maps/hokkaido1', 'https://calendar.google.com/event?hokkaido1',
    1, 2, 3,
    '請攜帶防寒衣物。', '探索北海道最美雪景與溫泉之旅。',
    'http://localhost:3000/uploads/seed/tour.svg',
    'http://localhost:3000/uploads/seed/tour.svg', '札幌夜景',
    'http://localhost:3000/uploads/seed/tour.svg', '小樽運河',
    'http://localhost:3000/uploads/seed/tour.svg', '登別溫泉',
    'http://localhost:3000/uploads/seed/tour.svg', '旭川動物園',
    'http://localhost:3000/uploads/seed/tour.svg', '富良野薰衣草',
    'http://localhost:3000/uploads/seed/tour.svg', '冰雪祭典',
    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
),
-- tourgroup: travel
(
    '22222222-bbbb-cccc-dddd-222222222222',
    'tourgroup', 'travel', 1,
    '馬爾地夫蜜月天堂 6 日', '享受專屬你的藍色海洋假期',
    (TIMESTAMP '2025-11-10 00:00:00' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), (TIMESTAMP '2025-11-15 23:59:59' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), 6, 98000,
    'Maldives', 'Male', '北馬列環礁私人島嶼',
    'https://goo.gl/maps/maldives1', 'https://calendar.google.com/event?maldives1',
    2, 1, 3,
    '請攜帶防曬用品。', '入住水上別墅，專屬浪漫行程。',
    'http://localhost:3000/uploads/seed/tour.svg',
    'http://localhost:3000/uploads/seed/tour.svg', '水上別墅景色',
    'http://localhost:3000/uploads/seed/tour.svg', '海上活動',
    'http://localhost:3000/uploads/seed/tour.svg', '私人沙灘',
    'http://localhost:3000/uploads/seed/tour.svg', '環礁浮潛',
    'http://localhost:3000/uploads/seed/tour.svg', 'SPA中心',
    'http://localhost:3000/uploads/seed/tour.svg', '夕陽巡航',
    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
),
-- backpacker: food
(
    '33333333-cccc-dddd-eeee-333333333333',
    'backpacker', 'food', 1,
    '大阪美食自由行', '胃袋的無限探險',
    null, null, 0, 15000,
    'Japan', 'Osaka', '道頓堀美食街',
    'https://goo.gl/maps/osaka1', 'https://calendar.google.com/event?osaka1',
    3, 1, 2,
    '請注意行程中包含生食餐點。', '深入大阪尋找道地美食與居酒屋。',
    'http://localhost:3000/uploads/seed/tour.svg',
    'http://localhost:3000/uploads/seed/tour.svg', '章魚燒',
    'http://localhost:3000/uploads/seed/tour.svg', '燒肉體驗',
    'http://localhost:3000/uploads/seed/tour.svg', '居酒屋文化',
    'http://localhost:3000/uploads/seed/tour.svg', '大阪壽司',
    'http://localhost:3000/uploads/seed/tour.svg', '道頓堀夜景',
    'http://localhost:3000/uploads/seed/tour.svg', '黑門市場',
    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
),
-- backpacker: spot
(
    '44444444-dddd-eeee-ffff-444444444444',
    'backpacker', 'spot', 1,
    '巴黎歷史建築巡禮', '在歷史的街道中穿梭',
    null, null, 0, 22000,
    'France', 'Paris', '巴黎拉丁區',
    'https://goo.gl/maps/paris2', 'https://calendar.google.com/event?paris2',
    1, 3, 2,
    '穿著舒適的步行鞋。', '漫步歷史古蹟與文學街區。',
    'http://localhost:3000/uploads/seed/tour.svg',
    'http://localhost:3000/uploads/seed/tour.svg', '巴黎聖母院',
    'http://localhost:3000/uploads/seed/tour.svg', '盧森堡公園',
    'http://localhost:3000/uploads/seed/tour.svg', '羅丹美術館',
    'http://localhost:3000/uploads/seed/tour.svg', '先賢祠',
    'http://localhost:3000/uploads/seed/tour.svg', '拉丁區書店',
    'http://localhost:3000/uploads/seed/tour.svg', '塞納河畔',
    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
),
-- backpacker: hotel
(
    '55555555-eeee-ffff-aaaa-555555555555',
    'backpacker', 'hotel', 1,
    '曼谷設計旅店探索', '感受泰式設計美學',
    null, null, 0, 9000,
    'Thailand', 'Bangkok', '曼谷素坤逸路',
    'https://goo.gl/maps/bangkok1', 'https://calendar.google.com/event?bangkok1',
    2, 1, 3,
    '入住時間依飯店規定。', '選擇最具設計感的平價住宿。',
    'http://localhost:3000/uploads/seed/tour.svg',
    'http://localhost:3000/uploads/seed/tour.svg', '曼谷設計旅館',
    'http://localhost:3000/uploads/seed/tour.svg', '夜市巡禮',
    'http://localhost:3000/uploads/seed/tour.svg', '昭披耶河景',
    'http://localhost:3000/uploads/seed/tour.svg', '大皇宮一日遊',
    'http://localhost:3000/uploads/seed/tour.svg', '文青咖啡店',
    'http://localhost:3000/uploads/seed/tour.svg', '市集探險',
    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
),
-- tourgroup: travel
(
    '66666666-ffff-aaaa-bbbb-666666666666',
    'tourgroup', 'travel', 1,
    '義大利深度文化之旅', '在藝術與美食中迷失',
    (TIMESTAMP '2025-10-15 00:00:00' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), (TIMESTAMP '2025-10-22 23:59:59' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), 8, 72000,
    'Italy', 'Rome', '羅馬市中心西班牙廣場',
    'https://goo.gl/maps/rome1', 'https://calendar.google.com/event?rome1',
    1, 2, 3,
    '行程部分需攀爬古蹟階梯。', '穿越千年歷史，體驗義式浪漫。',
    'http://localhost:3000/uploads/seed/tour.svg',
    'http://localhost:3000/uploads/seed/tour.svg', '羅馬競技場',
    'http://localhost:3000/uploads/seed/tour.svg', '聖彼得大教堂',
    'http://localhost:3000/uploads/seed/tour.svg', '特雷維噴泉',
    'http://localhost:3000/uploads/seed/tour.svg', '西班牙階梯',
    'http://localhost:3000/uploads/seed/tour.svg', '梵蒂岡博物館',
    'http://localhost:3000/uploads/seed/tour.svg', '羅馬廣場',
    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
),
-- backpacker: spot
(
    '77777777-aaaa-bbbb-cccc-777777777777',
    'backpacker', 'spot', 1,
    '首爾咖啡文青小旅行', '在咖啡香裡漫遊城市',
    null, null, 0, 9500,
    'Korea', 'Seoul', '弘大入口站周邊',
    'https://goo.gl/maps/seoul1', 'https://calendar.google.com/event?seoul1',
    3, 1, 2,
    '注意部分巷弄無電梯設施。', '探訪首爾最具文藝氣息的街區與咖啡店。',
    'http://localhost:3000/uploads/seed/tour.svg',
    'http://localhost:3000/uploads/seed/tour.svg', '延南洞文青街',
    'http://localhost:3000/uploads/seed/tour.svg', '首爾森林',
    'http://localhost:3000/uploads/seed/tour.svg', '聖水洞咖啡店',
    'http://localhost:3000/uploads/seed/tour.svg', '弘大藝術牆',
    'http://localhost:3000/uploads/seed/tour.svg', '城東區手作市集',
    'http://localhost:3000/uploads/seed/tour.svg', '夜市甜品巡禮',
    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
),
-- backpacker: hotel
(
    '88888888-bbbb-cccc-dddd-888888888888',
    'backpacker', 'hotel', 2,
    '清邁自然旅宿體驗', '在綠意環繞中放鬆身心',
    null, null, 0, 7800,
    'Thailand', 'Chiang Mai', '古城區瓦洛洛市場附近',
    'https://goo.gl/maps/chiangmai1', 'https://calendar.google.com/event?chiangmai1',
    2, 3, 1,
    '民宿僅提供基本設施，無電梯。', '在清邁體驗傳統泰北文化與自然風光。',
    'http://localhost:3000/uploads/seed/tour.svg',
    'http://localhost:3000/uploads/seed/tour.svg', '清邁古城',
    'http://localhost:3000/uploads/seed/tour.svg', '素貼山夜景',
    'http://localhost:3000/uploads/seed/tour.svg', '瓦洛洛市場',
    'http://localhost:3000/uploads/seed/tour.svg', '寧曼路商圈',
    'http://localhost:3000/uploads/seed/tour.svg', '周六市集',
    'http://localhost:3000/uploads/seed/tour.svg', '寺廟文化探索',
    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
),
-- backpacker: food
(
    '99999999-cccc-dddd-eeee-999999999999',
    'backpacker', 'food', 1,
    '高雄夜市美食攻略', '不容錯過的小吃巡禮',
    null, null, 0, 4200,
    'Taiwan', 'Kaohsiung', '六合夜市',
    'https://goo.gl/maps/kaohsiung1', 'https://calendar.google.com/event?kaohsiung1',
    1, 2, 3,
    '請自備零錢及環保餐具。', '從六合夜市吃到瑞豐夜市，探訪高雄最強美食。',
    'http://localhost:3000/uploads/seed/tour.svg',
    'http://localhost:3000/uploads/seed/tour.svg', '六合夜市美食',
    'http://localhost:3000/uploads/seed/tour.svg', '瑞豐夜市人氣小吃',
    'http://localhost:3000/uploads/seed/tour.svg', '旗津海鮮街',
    'http://localhost:3000/uploads/seed/tour.svg', '新崛江甜品',
    'http://localhost:3000/uploads/seed/tour.svg', '鹽埕區老店',
    'http://localhost:3000/uploads/seed/tour.svg', '高雄港夜景',
    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
),
-- tourgroup: travel
(
    '00000000-dddd-eeee-ffff-000000000000',
    'tourgroup', 'travel', 1,
    '紐西蘭壯麗景觀自駕遊', '開啟最自由的冒險',
    (TIMESTAMP '2025-11-05 00:00:00' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), (TIMESTAMP '2025-11-15 23:59:59' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), 11, 85000,
    'New Zealand', 'South Island', '基督城市中心',
    'https://goo.gl/maps/nz1', 'https://calendar.google.com/event?nz1',
    3, 1, 2,
    '請攜帶國際駕照並確保駕駛經驗。', '從冰河到峽灣，體驗純粹自然。',
    'http://localhost:3000/uploads/seed/tour.svg',
    'http://localhost:3000/uploads/seed/tour.svg', '庫克山冰川',
    'http://localhost:3000/uploads/seed/tour.svg', '皇后鎮湖光山色',
    'http://localhost:3000/uploads/seed/tour.svg', '米佛峽灣巡航',
    'http://localhost:3000/uploads/seed/tour.svg', '蒂卡波湖星空',
    'http://localhost:3000/uploads/seed/tour.svg', '箭鎮金礦小鎮',
    'http://localhost:3000/uploads/seed/tour.svg', '瓦納卡湖',
    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT DO NOTHING;

---- 6. 旅遊產品細項資料 "tour_detail"
INSERT INTO "tour_detail" (
    tour_detail_id, tour_id, feature_img1, feature_desc1, feature_img2, feature_desc2, feature_img3, feature_desc3, itinerary, created_at, updated_at
) VALUES
(
    'aaa11111-bbbb-2222-cccc-3333dddd4444',
    '11111111-aaaa-bbbb-cccc-111111111111',
    'http://localhost:3000/uploads/seed/feature.svg', '旭川雪祭典體驗',
    'http://localhost:3000/uploads/seed/feature.svg', '美瑛白金青池探訪',
    'http://localhost:3000/uploads/seed/feature.svg', '登別地獄谷探險',
    'Day1: 札幌市區巡禮,Day2: 小樽運河,Day3: 美瑛青池,Day4: 登別溫泉,Day5: 旭川雪祭',
    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
),
(
    'bbb22222-cccc-3333-dddd-4444eeee5555',
    '22222222-bbbb-cccc-dddd-222222222222',
    'http://localhost:3000/uploads/seed/feature.svg', '水上別墅享受',
    'http://localhost:3000/uploads/seed/feature.svg', '私人島嶼浮潛',
    'http://localhost:3000/uploads/seed/feature.svg', '夕陽巡航浪漫',
    'Day1: 抵達馬列,Day2: 私人島浮潛,Day3: SPA與日光浴,Day4: 水上別墅活動,Day5: 浪漫晚宴,Day6: 自由活動',
    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
),
(
    'ccc33333-dddd-4444-eeee-5555ffff6666',
    '66666666-ffff-aaaa-bbbb-666666666666',
    'http://localhost:3000/uploads/seed/feature.svg', '羅馬競技場探訪',
    'http://localhost:3000/uploads/seed/feature.svg', '托斯卡尼鄉村漫遊',
    'http://localhost:3000/uploads/seed/feature.svg', '梵蒂岡藝術之旅',
    'Day1: 羅馬市區巡禮,Day2: 梵蒂岡博物館,Day3: 羅馬古城,Day4: 托斯卡尼自由行,Day5: 比薩斜塔,Day6: 佛羅倫斯藝術街區,Day7: 羅馬購物日,Day8: 返回',
    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
),
(
    'ddd44444-eeee-5555-ffff-6666aaaa7777',
    '00000000-dddd-eeee-ffff-000000000000',
    'http://localhost:3000/uploads/seed/feature.svg', '庫克山冰河健行',
    'http://localhost:3000/uploads/seed/feature.svg', '蒂卡波星空夜拍',
    'http://localhost:3000/uploads/seed/feature.svg', '米佛峽灣巡航體驗',
    'Day1: 基督城市區探索,Day2: 蒂卡波湖星空,Day3: 庫克山健行,Day4: 皇后鎮自由行,Day5: 米佛峽灣巡航,Day6: 弗朗茲約瑟夫冰河健行,Day7-11: 南島深度自由探索',
    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
),
(
    'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
    '44444444-dddd-eeee-ffff-444444444444',
    'http://localhost:3000/uploads/seed/feature.svg', '巴黎聖母院巡禮',
    'http://localhost:3000/uploads/seed/feature.svg', '塞納河畔夜遊',
    'http://localhost:3000/uploads/seed/feature.svg', '拉丁區藝術巷弄',
    'Day1: 巴黎聖母院參觀,Day2: 塞納河遊船,Day3: 拉丁區文學之旅',
    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
),
(
    'b2c3d4e5-f678-90ab-cdef-234567890abc',
    '77777777-aaaa-bbbb-cccc-777777777777',
    'http://localhost:3000/uploads/seed/feature.svg', '延南洞文青街探訪',
    'http://localhost:3000/uploads/seed/feature.svg', '聖水洞咖啡巡禮',
    'http://localhost:3000/uploads/seed/feature.svg', '弘大街頭藝術欣賞',
    'Day1: 延南洞文青咖啡館巡禮,Day2: 聖水洞手作街探險,Day3: 弘大夜市與藝術街探索',
    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT DO NOTHING;

----- 7. 美食專區資料 "restaurant"
INSERT INTO "restaurant" (
    restaurant_id, tour_id, reservation_limit, website_info, website_url, created_at, updated_at
) VALUES
(
    'aaa11111-bbbb-2222-cccc-3333dddd4444',
    '33333333-cccc-dddd-eeee-333333333333',
    50,
    '大阪當地超人氣餐廳集合，無需排隊即可入場。',
    'https://example.com/osaka-food-tour',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
),
(
    'bbb22222-cccc-3333-dddd-4444eeee5555',
    '99999999-cccc-dddd-eeee-999999999999',
    30,
    '高雄夜市美食攻略，預約即享專屬美食地圖。',
    'https://example.com/kaohsiung-food-tour',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
)
ON CONFLICT DO NOTHING;

----- 8. 美食專區營業資料 "restaurant_business"
INSERT INTO "restaurant_business" (
    restaurant_business_id, restaurant_id, week, business_hours, created_at, updated_at
) VALUES
('0d0a9f2e-5e64-4c88-8f58-1ad9aa5f0c11', 'aaa11111-bbbb-2222-cccc-3333dddd4444', 'Monday',    '11:00~14:00, 17:00~21:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('1b7f6b2a-bc7b-4687-9c22-7d6cf26e42de', 'aaa11111-bbbb-2222-cccc-3333dddd4444', 'Tuesday',   '11:00~14:00, 17:00~21:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('2c2c7af5-73e5-49be-8af6-7f23e21d8e8f', 'aaa11111-bbbb-2222-cccc-3333dddd4444', 'Wednesday', '11:00~14:00, 17:00~21:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('3d53e1fc-cc0b-4cf4-9e02-c7c9571dbb3f', 'aaa11111-bbbb-2222-cccc-3333dddd4444', 'Thursday',  '11:00~14:00, 17:00~21:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('4a8a8b1d-1b7c-4536-bf2e-ef9a19a7ec0f', 'aaa11111-bbbb-2222-cccc-3333dddd4444', 'Friday',    '11:00~14:00, 17:00~22:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('5e8e24e9-3a3d-4a5a-8080-1dcf918d0d25', 'aaa11111-bbbb-2222-cccc-3333dddd4444', 'Saturday',  '11:00~15:00, 17:00~22:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('6f26dc1f-81ff-4b09-89f5-987b65d9e022', 'aaa11111-bbbb-2222-cccc-3333dddd4444', 'Sunday',    '11:00~15:00, 17:00~21:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('7dbb5c41-00a9-46de-b94c-97c0ef019c87', 'bbb22222-cccc-3333-dddd-4444eeee5555', 'Monday',    '17:00~23:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('8b0d3d5a-c71f-4b2b-8e02-07dc6aa0f963', 'bbb22222-cccc-3333-dddd-4444eeee5555', 'Tuesday',   '17:00~23:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('9abced12-94a1-47c9-bd78-2b2c8f9ea6d1', 'bbb22222-cccc-3333-dddd-4444eeee5555', 'Wednesday', '17:00~23:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('ac05fc32-cf1b-4f0b-8822-8122e6c140be', 'bbb22222-cccc-3333-dddd-4444eeee5555', 'Thursday',  '17:00~23:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('bd6b8ab7-2838-4b8a-bb9a-93e8126b0a26', 'bbb22222-cccc-3333-dddd-4444eeee5555', 'Friday',    '17:00~00:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('ca7813fc-21f4-4e48-bb8f-2f4c1a8377e3', 'bbb22222-cccc-3333-dddd-4444eeee5555', 'Saturday',  '17:00~00:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('db3e5f17-63ca-4c55-9200-9bcb1b4fa3fb', 'bbb22222-cccc-3333-dddd-4444eeee5555', 'Sunday',    '17:00~23:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)

ON CONFLICT DO NOTHING;

----- 9. 美食專區菜單資料 "restaurant_menu"
INSERT INTO "restaurant_menu" (
    restaurant_menu_id, restaurant_id, name, price, description, created_at, updated_at
) VALUES
-- 大阪美食自由行餐廳菜單
('11111111-aaaa-bbbb-cccc-111111111111', 'aaa11111-bbbb-2222-cccc-3333dddd4444', '章魚燒', 150.0, '外酥內軟，經典大阪街頭小吃。', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('22222222-bbbb-cccc-dddd-222222222222', 'aaa11111-bbbb-2222-cccc-3333dddd4444', '大阪燒', 300.0, '層層堆疊的美味與滿滿高麗菜。', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('33333333-cccc-dddd-eeee-333333333333', 'aaa11111-bbbb-2222-cccc-3333dddd4444', '串燒拼盤', 450.0, '嚴選牛、豬、雞肉串搭配秘製醬汁。', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('44444444-dddd-eeee-ffff-444444444444', 'bbb22222-cccc-3333-dddd-4444eeee5555', '鹽酥雞', 80.0, '酥脆香嫩的經典夜市小吃。', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('55555555-eeee-ffff-aaaa-555555555555', 'bbb22222-cccc-3333-dddd-4444eeee5555', '滷味拼盤', 120.0, '多樣滷味搭配獨門滷汁，回味無窮。', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('66666666-ffff-aaaa-bbbb-666666666666', 'bbb22222-cccc-3333-dddd-4444eeee5555', '木瓜牛奶', 70.0, '高雄人氣飲品，清甜滑順解渴。', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
ON CONFLICT DO NOTHING;

---- 10. 飯店專區資料 "hotel"
INSERT INTO "hotel" (
    hotel_id, tour_id, facility_desc, food_desc, room_desc, leisure_desc, traffic_desc, other_desc, created_at, updated_at
) VALUES
(
    '11111111-aaaa-bbbb-cccc-111111111111',
    '55555555-eeee-ffff-aaaa-555555555555',
    '24 小時櫃台服務, 免費 Wi-Fi, 行李寄存服務, 毛巾, 客房清潔服務',
    '早餐供應, 餐廳/咖啡館, 飲水機',
    '冷氣/暖氣, 獨立衛浴, 電視（有線/第四台）, 小冰箱',
    '健身房, SPA/按摩服務, 游泳池（室外）',
    '停車場, 租車服務, 接駁巴士（市區）',
    '外幣兌換, 叫車/叫計程車, 洗衣服務/自助洗衣',
    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
),
(
    '22222222-bbbb-cccc-dddd-222222222222',
    '88888888-bbbb-cccc-dddd-888888888888',
    '24 小時櫃台服務, 免費 Wi-Fi, 行李寄存服務, 提供嬰兒床/收嬰',
    '早餐供應, 酒吧或 Lounge 酒廊',
    '冷氣/暖氣, 獨立衛浴, 電視（有線/第四台）, 咖啡機/加熱水壺',
    '健身房, 兒童遊戲區, 娛樂區/圖書館',
    '停車場, 租車服務, 機場接送服務（需預約）',
    '外幣兌換, 褓姆服務/吸菸區',
    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT DO NOTHING;

---- 11. 飯店專區客房資料 "hotel_room"
INSERT INTO "hotel_room" (
    hotel_room_id, hotel_id, title, capacity, room_count, image, image_desc, created_at, updated_at
) VALUES
(
    'aaa11111-bbbb-2222-cccc-3333dddd4444',
    '11111111-aaaa-bbbb-cccc-111111111111',
    '設計雙人房',
    2,
    10,
    'http://localhost:3000/uploads/seed/tour.svg',
    '現代簡約風格，附舒適大床與書桌。',
    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
),
(
    'aaa11111-bbbb-3333-cccc-4444dddd5555',
    '11111111-aaaa-bbbb-cccc-111111111111',
    '豪華家庭房',
    4,
    5,
    'http://localhost:3000/uploads/seed/tour.svg',
    '寬敞空間，適合親子同住，附沙發床。',
    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
),
(
    'bbb22222-cccc-4444-dddd-5555eeee6666',
    '22222222-bbbb-cccc-dddd-222222222222',
    '自然雙人房',
    2,
    8,
    'http://localhost:3000/uploads/seed/tour.svg',
    '溫暖木質設計，大面窗採光。',
    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
),
(
    'bbb22222-cccc-5555-dddd-6666eeee7777',
    '22222222-bbbb-cccc-dddd-222222222222',
    '親子套房',
    4,
    6,
    'http://localhost:3000/uploads/seed/tour.svg',
    '親子專用設施，兒童遊戲空間。',
    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT DO NOTHING;

---- 12. 重要通知資料(促銷/異動) "notification"
INSERT INTO "notification" (
    notification_id, tour_id, type, start_date, end_date, discount, promo_price, change_desc, created_at, updated_at
) VALUES
(
    '11111111-aaaa-bbbb-cccc-111111111111',
    '11111111-aaaa-bbbb-cccc-111111111111',  -- 北海道雪景
    '促銷',
    (TIMESTAMP '2025-11-01 00:00:00' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'),
    (TIMESTAMP '2025-11-30 23:59:59' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'),
    10.0,
    40500.0,
    NULL,
    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
),
(
    '22222222-bbbb-cccc-dddd-222222222222',
    '22222222-bbbb-cccc-dddd-222222222222',  -- 馬爾地夫蜜月
    '促銷',
    (TIMESTAMP '2025-10-01 00:00:00' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'),
    (TIMESTAMP '2025-10-31 23:59:59' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'),
    15.0,
    83300.0,
    NULL,
    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
),
(
    '33333333-cccc-dddd-eeee-333333333333',
    '66666666-ffff-aaaa-bbbb-666666666666',  -- 義大利深度文化之旅
    '異動',
    NULL,
    NULL,
    NULL,
    NULL,
    '因故調整行程，第4日改至比薩市區自由行。',
    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
),
(
    '44444444-dddd-eeee-ffff-444444444444',
    '00000000-dddd-eeee-ffff-000000000000',  -- 紐西蘭壯麗自駕
    '異動',
    NULL,
    NULL,
    NULL,
    NULL,
    '新增米佛峽灣遊船行程，行程時間延長1天。',
    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT DO NOTHING;

---- 13. 國家資料 "country"
INSERT INTO "country" (country_id, name, created_at) VALUES
('11111111-1111-1111-1111-111111111111', '台灣', CURRENT_TIMESTAMP),
('22222222-2222-2222-2222-222222222222', '日本', CURRENT_TIMESTAMP),
('33333333-3333-3333-3333-333333333333', '韓國', CURRENT_TIMESTAMP),
('44444444-4444-4444-4444-444444444444', '香港', CURRENT_TIMESTAMP),
('55555555-5555-5555-5555-555555555555', '澳門', CURRENT_TIMESTAMP),
('66666666-6666-6666-6666-666666666666', '中國', CURRENT_TIMESTAMP),
('77777777-7777-7777-7777-777777777777', '泰國', CURRENT_TIMESTAMP),
('88888888-8888-8888-8888-888888888888', '越南', CURRENT_TIMESTAMP),
('99999999-9999-9999-9999-999999999999', '新加坡', CURRENT_TIMESTAMP),
('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', '馬來西亞', CURRENT_TIMESTAMP),
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', '印尼', CURRENT_TIMESTAMP),
('cccccccc-cccc-cccc-cccc-cccccccccccc', '菲律賓', CURRENT_TIMESTAMP),
('dddddddd-dddd-dddd-dddd-dddddddddddd', '印度', CURRENT_TIMESTAMP),
('eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee', '英國', CURRENT_TIMESTAMP),
('ffffffff-ffff-ffff-ffff-ffffffffffff', '法國', CURRENT_TIMESTAMP),
('11111111-aaaa-bbbb-cccc-111111111111', '德國', CURRENT_TIMESTAMP),
('22222222-bbbb-cccc-dddd-222222222222', '義大利', CURRENT_TIMESTAMP),
('33333333-cccc-dddd-eeee-333333333333', '西班牙', CURRENT_TIMESTAMP),
('44444444-dddd-eeee-ffff-444444444444', '瑞士', CURRENT_TIMESTAMP),
('55555555-eeee-ffff-aaaa-555555555555', '荷蘭', CURRENT_TIMESTAMP),
('66666666-ffff-aaaa-bbbb-666666666666', '捷克', CURRENT_TIMESTAMP),
('77777777-aaaa-bbbb-cccc-777777777777', '奧地利', CURRENT_TIMESTAMP),
('88888888-bbbb-cccc-dddd-888888888888', '芬蘭', CURRENT_TIMESTAMP),
('99999999-cccc-dddd-eeee-999999999999', '冰島', CURRENT_TIMESTAMP),
('aaaaaaa1-dddd-eeee-ffff-aaaaaaa1aaaa', '挪威', CURRENT_TIMESTAMP),
('bbbbbbb2-eeee-ffff-aaaa-bbbbbbb2bbbb', '丹麥', CURRENT_TIMESTAMP),
('ccccccc3-ffff-aaaa-bbbb-ccccccc3cccc', '希臘', CURRENT_TIMESTAMP),
('ddddddd4-aaaa-bbbb-cccc-ddddddd4dddd', '美國', CURRENT_TIMESTAMP),
('eeeeeee5-bbbb-cccc-dddd-eeeeeee5eeee', '加拿大', CURRENT_TIMESTAMP),
('fffffff6-cccc-dddd-eeee-fffffff6ffff', '墨西哥', CURRENT_TIMESTAMP),
('aaaaaaa7-dddd-eeee-ffff-aaaaaaa7aaaa', '巴西', CURRENT_TIMESTAMP),
('bbbbbbb8-eeee-ffff-aaaa-bbbbbbb8bbbb', '澳大利亞', CURRENT_TIMESTAMP),
('ccccccc9-ffff-aaaa-bbbb-ccccccc9cccc', '紐西蘭', CURRENT_TIMESTAMP),
('ddddddd0-aaaa-bbbb-cccc-ddddddd0dddd', '阿聯酋', CURRENT_TIMESTAMP),
('eeeeeee1-bbbb-cccc-dddd-eeeeeee1eeee', '土耳其', CURRENT_TIMESTAMP),
('fffffff2-cccc-dddd-eeee-fffffff2ffff', '埃及', CURRENT_TIMESTAMP),
('aaaaaaa3-dddd-eeee-ffff-aaaaaaa3aaaa', '南非', CURRENT_TIMESTAMP)
ON CONFLICT DO NOTHING;

---- 14. 地區資料 "region"
INSERT INTO "region" (region_id, country_id, name, created_at) VALUES
('cb64f74c-af9c-5dac-8d2c-c0e85fe57cfd', '11111111-1111-1111-1111-111111111111', '台北市', CURRENT_TIMESTAMP),
('87144a63-92e1-5c97-8243-d49f7baa2feb', '11111111-1111-1111-1111-111111111111', '新北市', CURRENT_TIMESTAMP),
('77b19dd1-b717-5582-868e-bce4d67fccca', '11111111-1111-1111-1111-111111111111', '桃園市', CURRENT_TIMESTAMP),
('d81998de-11a5-595a-8354-9939a9b55e41', '11111111-1111-1111-1111-111111111111', '台中市', CURRENT_TIMESTAMP),
('6404929c-9ec2-51f4-9c46-a6bc0c27f56c', '11111111-1111-1111-1111-111111111111', '台南市', CURRENT_TIMESTAMP),
('ccfebd88-0203-5647-b44f-bdd3eeb7291a', '11111111-1111-1111-1111-111111111111', '高雄市', CURRENT_TIMESTAMP),
('f1613b5b-2611-590f-9cdc-8af45872210f', '11111111-1111-1111-1111-111111111111', '基隆市', CURRENT_TIMESTAMP),
('e9eecc64-7aa2-5e37-98f3-f12a5e1f2e74', '11111111-1111-1111-1111-111111111111', '新竹市', CURRENT_TIMESTAMP),
('2fdcd38c-421b-5650-b469-fdb0dc54c5a6', '11111111-1111-1111-1111-111111111111', '新竹縣', CURRENT_TIMESTAMP),
('ec27abe5-68d0-5b8e-90ac-556cf1b5ecbb', '11111111-1111-1111-1111-111111111111', '苗栗縣', CURRENT_TIMESTAMP),
('33cc6951-6d3b-52a7-b1cc-c6b17ffbf9e9', '11111111-1111-1111-1111-111111111111', '彰化縣', CURRENT_TIMESTAMP),
('a0ec8f5c-6f63-55f3-8dee-12c3c1b33d9b', '11111111-1111-1111-1111-111111111111', '南投縣', CURRENT_TIMESTAMP),
('949d6b20-dbbd-5ba1-acbd-885d09ceb611', '11111111-1111-1111-1111-111111111111', '雲林縣', CURRENT_TIMESTAMP),
('c053f2bd-9c63-592a-a6f7-8f5f84118661', '11111111-1111-1111-1111-111111111111', '嘉義市', CURRENT_TIMESTAMP),
('7fab29b5-6898-5f76-86fc-7d2cac423ffe', '11111111-1111-1111-1111-111111111111', '嘉義縣', CURRENT_TIMESTAMP),
('4a5d6973-1cae-5442-bfca-d192426d777a', '11111111-1111-1111-1111-111111111111', '屏東縣', CURRENT_TIMESTAMP),
('7e5d78f2-b916-5f94-845b-822013d6a2f1', '11111111-1111-1111-1111-111111111111', '宜蘭縣', CURRENT_TIMESTAMP),
('268b84ed-1e3f-5c0e-815c-33f22b539f44', '11111111-1111-1111-1111-111111111111', '花蓮縣', CURRENT_TIMESTAMP),
('fbc88be6-c17a-52a9-b892-6395cb0e6a5c', '11111111-1111-1111-1111-111111111111', '台東縣', CURRENT_TIMESTAMP),
('d746330c-591a-5f4b-bfab-0d597e5d894f', '11111111-1111-1111-1111-111111111111', '澎湖縣', CURRENT_TIMESTAMP),
('a0f93840-754a-5b81-a80b-2e7179ab25d3', '11111111-1111-1111-1111-111111111111', '金門縣', CURRENT_TIMESTAMP),
('fa5cebe4-6747-5f34-823d-7af574ebe1fd', '11111111-1111-1111-1111-111111111111', '連江縣', CURRENT_TIMESTAMP),
('83d0d22a-9db4-5d56-9399-56d7359223e1', '22222222-2222-2222-2222-222222222222', '東京', CURRENT_TIMESTAMP),
('825f5c40-cf33-57e8-bbd1-3f950274ba93', '22222222-2222-2222-2222-222222222222', '大阪', CURRENT_TIMESTAMP),
('72e19883-d313-5238-9679-38bbe34b27ef', '22222222-2222-2222-2222-222222222222', '京都', CURRENT_TIMESTAMP),
('f845c411-1e7d-590d-8ef4-2a5b73f96da3', '22222222-2222-2222-2222-222222222222', '北海道', CURRENT_TIMESTAMP),
('3df747f3-cded-5ffc-aacd-a0b1cf2d997d', '22222222-2222-2222-2222-222222222222', '沖繩', CURRENT_TIMESTAMP),
('24a48dba-9380-560e-be26-833e336c0adc', '33333333-3333-3333-3333-333333333333', '首爾', CURRENT_TIMESTAMP),
('1726023e-0060-5505-a9b8-5fdd179b2dd1', '33333333-3333-3333-3333-333333333333', '釜山', CURRENT_TIMESTAMP),
('851cf028-7f36-5625-bfae-9fb2e43d0c48', '33333333-3333-3333-3333-333333333333', '濟州島', CURRENT_TIMESTAMP),
('708aebfb-7859-5157-8ab8-36c543d5a445', '44444444-4444-4444-4444-444444444444', '香港島', CURRENT_TIMESTAMP),
('23434959-79b7-5e3a-aa75-e7af2186467f', '44444444-4444-4444-4444-444444444444', '九龍', CURRENT_TIMESTAMP),
('a93e9517-59b6-5063-b976-33a16965f6de', '44444444-4444-4444-4444-444444444444', '新界', CURRENT_TIMESTAMP),
('2e9418a1-8875-5cf6-b8de-65a40ce3d10d', '55555555-5555-5555-5555-555555555555', '澳門半島', CURRENT_TIMESTAMP),
('0120527b-00df-5a76-8a10-40554b0d1050', '55555555-5555-5555-5555-555555555555', '氹仔', CURRENT_TIMESTAMP),
('8965aaf9-3e67-5092-ab72-137e89e1ddf2', '55555555-5555-5555-5555-555555555555', '路氹城', CURRENT_TIMESTAMP),
('f08eb7e1-f244-5e7b-81f7-1336f4622ff4', '66666666-6666-6666-6666-666666666666', '北京', CURRENT_TIMESTAMP),
('3ad7b043-ff08-5ec3-8331-618238b0efc3', '66666666-6666-6666-6666-666666666666', '上海', CURRENT_TIMESTAMP),
('d09e3022-7fad-5251-8673-e2bce26da977', '66666666-6666-6666-6666-666666666666', '廣州', CURRENT_TIMESTAMP),
('3435ed7c-ac23-5625-92ab-aa06bdfeaa9d', '66666666-6666-6666-6666-666666666666', '成都', CURRENT_TIMESTAMP),
('a9c7c493-b586-5e5a-86ed-a35014a1887a', '66666666-6666-6666-6666-666666666666', '西安', CURRENT_TIMESTAMP),
('542c99d4-d76f-5d64-a533-d68e193ef9e4', 'ddddddd4-aaaa-bbbb-cccc-ddddddd4dddd', '紐約', CURRENT_TIMESTAMP),
('a7c9da20-c01a-5c7e-a72c-a1a8e7de9495', 'ddddddd4-aaaa-bbbb-cccc-ddddddd4dddd', '洛杉磯', CURRENT_TIMESTAMP),
('30076da8-a513-57cc-adc0-60e5ad18d274', 'ddddddd4-aaaa-bbbb-cccc-ddddddd4dddd', '舊金山', CURRENT_TIMESTAMP),
('9e73d757-a4ee-5940-b314-87b6bfa31d0b', 'ddddddd4-aaaa-bbbb-cccc-ddddddd4dddd', '拉斯維加斯', CURRENT_TIMESTAMP),
('fe1069a7-f59d-5e6d-90ae-14d79bc6e2d4', 'ddddddd4-aaaa-bbbb-cccc-ddddddd4dddd', '夏威夷', CURRENT_TIMESTAMP),
('2171171d-7301-5ed8-b0f6-7932c1d5b6a9', 'eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee', '倫敦', CURRENT_TIMESTAMP),
('0391e4f9-45f4-512c-9c25-c11622804039', 'eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee', '曼徹斯特', CURRENT_TIMESTAMP),
('8530fe8f-6bc1-5a46-b7c4-ac3ecc4f112e', 'eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee', '愛丁堡', CURRENT_TIMESTAMP),
('6a898807-48cc-5755-ba8f-df797a29a801', 'ffffffff-ffff-ffff-ffff-ffffffffffff', '巴黎', CURRENT_TIMESTAMP),
('4063f438-af15-5300-8f5d-a3bbc4542b07', 'ffffffff-ffff-ffff-ffff-ffffffffffff', '里昂', CURRENT_TIMESTAMP),
('1ea88a02-4e65-5a10-b177-9fb148f22929', 'ffffffff-ffff-ffff-ffff-ffffffffffff', '尼斯', CURRENT_TIMESTAMP),
('d08ed0cf-4f33-522f-957e-d476179974d4', '77777777-7777-7777-7777-777777777777', '曼谷', CURRENT_TIMESTAMP),
('8356b47d-2bca-51a2-91dd-671d846c5a42', '77777777-7777-7777-7777-777777777777', '清邁', CURRENT_TIMESTAMP),
('7c959dba-c5a0-520e-a07d-b323abbdd3eb', '77777777-7777-7777-7777-777777777777', '普吉島', CURRENT_TIMESTAMP),
('c970d486-6ef9-5fbd-86b2-ddaeed1102f9', '77777777-7777-7777-7777-777777777777', '芭達雅', CURRENT_TIMESTAMP),
('6bf7261a-3c31-5ffb-9fd4-d5971e73fe58', '88888888-8888-8888-8888-888888888888', '胡志明市', CURRENT_TIMESTAMP),
('694bc44c-45a2-5a11-abba-7005757553f8', '88888888-8888-8888-8888-888888888888', '河內', CURRENT_TIMESTAMP),
('abbc749e-ed80-5873-a018-6ffabfff9ef1', '88888888-8888-8888-8888-888888888888', '峴港', CURRENT_TIMESTAMP),
('49cff71d-11f1-5eff-b24b-6612c0016762', '99999999-9999-9999-9999-999999999999', '新加坡', CURRENT_TIMESTAMP),
('fdc43f78-eb2a-587f-8ed1-cd18b3ea5643', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', '吉隆坡', CURRENT_TIMESTAMP),
('dab7f74b-282f-596c-b647-3d9c1d0f29c4', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', '檳城', CURRENT_TIMESTAMP),
('81c2794a-174e-5746-8dd2-d0b4f06c8214', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', '沙巴', CURRENT_TIMESTAMP),
('64d93692-6801-5b38-a067-8b622dbefee1', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', '峇里島', CURRENT_TIMESTAMP),
('f91b9ea3-ac40-5925-bd32-658c9db0a781', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', '雅加達', CURRENT_TIMESTAMP),
('df4a268b-2f87-50aa-a82d-4790b28ad373', 'cccccccc-cccc-cccc-cccc-cccccccccccc', '馬尼拉', CURRENT_TIMESTAMP),
('d78fa064-b04b-5cfa-b615-e4efb93bf37c', 'cccccccc-cccc-cccc-cccc-cccccccccccc', '宿霧', CURRENT_TIMESTAMP),
('c9573a3e-f5ff-570d-86db-6322bfc17304', 'cccccccc-cccc-cccc-cccc-cccccccccccc', '長灘島', CURRENT_TIMESTAMP),
('78cb6a85-2bd7-59df-8e92-b8aab36394a5', 'dddddddd-dddd-dddd-dddd-dddddddddddd', '德里', CURRENT_TIMESTAMP),
('2969b79d-d3b0-52df-a72f-e64a11a4b922', 'dddddddd-dddd-dddd-dddd-dddddddddddd', '孟買', CURRENT_TIMESTAMP),
('bf2dfeaa-346b-51a1-a7b4-573820a41851', 'dddddddd-dddd-dddd-dddd-dddddddddddd', '齋浦爾', CURRENT_TIMESTAMP),
('d71b77e7-9c23-5655-ab97-5d55902d8c91', 'bbbbbbb8-eeee-ffff-aaaa-bbbbbbb8bbbb', '雪梨', CURRENT_TIMESTAMP),
('a7bb1215-385c-5fa3-ab11-b7b840108dd0', 'bbbbbbb8-eeee-ffff-aaaa-bbbbbbb8bbbb', '墨爾本', CURRENT_TIMESTAMP),
('c44e9538-753b-56a6-83d0-54431c5cd62a', 'bbbbbbb8-eeee-ffff-aaaa-bbbbbbb8bbbb', '布里斯本', CURRENT_TIMESTAMP),
('00cecaec-c794-5bec-891c-e0bd1a85d1fb', 'bbbbbbb8-eeee-ffff-aaaa-bbbbbbb8bbbb', '黃金海岸', CURRENT_TIMESTAMP),
('46f7bc00-8f9d-5de1-bffb-cbaf6dc71b0c', 'ccccccc9-ffff-aaaa-bbbb-ccccccc9cccc', '奧克蘭', CURRENT_TIMESTAMP),
('9d428a2b-0769-51d2-80d2-1415353b3b00', 'ccccccc9-ffff-aaaa-bbbb-ccccccc9cccc', '皇后鎮', CURRENT_TIMESTAMP),
('874f7bb6-1057-5a7d-88dc-168e35c5a5e5', 'ccccccc9-ffff-aaaa-bbbb-ccccccc9cccc', '基督城', CURRENT_TIMESTAMP),
('f740c093-eb76-56aa-8f27-d88043c8c3bb', 'ddddddd0-aaaa-bbbb-cccc-ddddddd0dddd', '杜拜', CURRENT_TIMESTAMP),
('3eb5ce0a-ff21-5bf6-9bd2-21787782b253', 'ddddddd0-aaaa-bbbb-cccc-ddddddd0dddd', '阿布達比', CURRENT_TIMESTAMP),
('54a273d0-c25d-5d06-bdfc-d218cf40e7e6', 'eeeeeee1-bbbb-cccc-dddd-eeeeeee1eeee', '伊斯坦堡', CURRENT_TIMESTAMP),
('5d41c87e-f6f4-5680-afda-3a0ac8bc09fb', 'eeeeeee1-bbbb-cccc-dddd-eeeeeee1eeee', '卡帕多奇亞', CURRENT_TIMESTAMP),
('a6008f4c-69d3-5beb-a194-10dcc4ff4c29', 'eeeeeee1-bbbb-cccc-dddd-eeeeeee1eeee', '安塔利亞', CURRENT_TIMESTAMP),
('41bdca4b-a9f3-5ac9-8931-9c13146e162f', 'fffffff2-cccc-dddd-eeee-fffffff2ffff', '開羅', CURRENT_TIMESTAMP),
('e3fdbf55-2172-54ee-9c5d-e8b7e69656ef', 'fffffff2-cccc-dddd-eeee-fffffff2ffff', '盧克索', CURRENT_TIMESTAMP),
('afccbd86-f5dc-55c4-836e-412731ea7af6', 'aaaaaaa3-dddd-eeee-ffff-aaaaaaa3aaaa', '開普敦', CURRENT_TIMESTAMP),
('94800d7b-776f-527f-86bd-e1a27da4dec8', 'aaaaaaa3-dddd-eeee-ffff-aaaaaaa3aaaa', '約翰尼斯堡', CURRENT_TIMESTAMP)
ON CONFLICT DO NOTHING;

---- 15. 購物車大項目資料 "cart"
INSERT INTO cart (cart_id, user_id, total_price) VALUES
('7bc2f92f-dafe-4cb2-9211-ffc67f16822e', 'a1b2c3d4-e5f6-7890-abcd-ef1234567890', 8721.69),
('83018530-f182-4734-afc2-cf4ecc96802d', 'a1b2c3d4-e5f6-7890-abcd-ef1234567890', 6263.64),
('65d6a65f-bcd8-4970-bf47-e28ae67a1c11', 'b2c3d4e5-f678-90ab-cdef-234567890abc', 3576.74),
('9221921d-33b0-4273-8e07-5fbb22acb772', 'b2c3d4e5-f678-90ab-cdef-234567890abc', 5769.06),
('7c09b1e1-8edc-44a7-a847-bdccf3153cfd', 'c3d4e5f6-7890-abcd-ef12-34567890abcd', 1610.73),
('08b4e271-f584-4297-9441-a299afb81098', 'c3d4e5f6-7890-abcd-ef12-34567890abcd', 6482.73)
ON CONFLICT DO NOTHING;

---- 16. 購物車細項資料 "cart_item"
INSERT INTO cart_item (cart_item_id, cart_id, tour_id, quantity, start_date, end_date, room_type) VALUES
('c5cefe38-ff77-497c-b3fb-2831bbfb898c', '65d6a65f-bcd8-4970-bf47-e28ae67a1c11', '99999999-cccc-dddd-eeee-999999999999', 2, (TIMESTAMP '2025-05-18' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), NULL, NULL),
('084a3d2b-f8d8-47f5-a977-47f225871375', '08b4e271-f584-4297-9441-a299afb81098', '22222222-bbbb-cccc-dddd-222222222222', 3, (TIMESTAMP '2025-11-10' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), (TIMESTAMP '2025-11-15' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), NULL),
('4936201b-d691-460b-97d0-000afae599c3', '7c09b1e1-8edc-44a7-a847-bdccf3153cfd', '11111111-aaaa-bbbb-cccc-111111111111', 1, (TIMESTAMP '2025-12-01' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), (TIMESTAMP '2025-12-05' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), NULL),
('f0e74ade-183f-4648-b9fe-cbb23458b89c', '9221921d-33b0-4273-8e07-5fbb22acb772', '88888888-bbbb-cccc-dddd-888888888888', 4, (TIMESTAMP '2025-05-19' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), (TIMESTAMP '2025-05-20' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), '豪華家庭房'),
('ecc926ca-d9f6-422f-8366-5d273236051b', '08b4e271-f584-4297-9441-a299afb81098', '44444444-dddd-eeee-ffff-444444444444', 3, (TIMESTAMP '2025-05-15' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), (TIMESTAMP '2025-05-16' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), NULL),
('f348640b-6ca0-4168-8615-6b19b4baf588', '65d6a65f-bcd8-4970-bf47-e28ae67a1c11', '66666666-ffff-aaaa-bbbb-666666666666', 5, (TIMESTAMP '2025-10-15' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), (TIMESTAMP '2025-10-22' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), NULL),
('70cc5744-2a87-4193-b503-1a5c73dc0b0c', '9221921d-33b0-4273-8e07-5fbb22acb772', '55555555-eeee-ffff-aaaa-555555555555', 2, (TIMESTAMP '2025-05-14' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), (TIMESTAMP '2025-05-15' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), '設計雙人房'),
('faa39aa2-6715-4dfa-bbac-2c6b1dc7de37', '65d6a65f-bcd8-4970-bf47-e28ae67a1c11', '00000000-dddd-eeee-ffff-000000000000', 3, (TIMESTAMP '2025-11-05' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), (TIMESTAMP '2025-11-15' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), NULL),
('c4b9e4b5-d0e9-4e5b-8884-7b115b6877de', '7c09b1e1-8edc-44a7-a847-bdccf3153cfd', '77777777-aaaa-bbbb-cccc-777777777777', 2, (TIMESTAMP '2025-05-13' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), (TIMESTAMP '2025-05-14' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), NULL),
('53f15e11-2350-4d9d-ade4-f4483af848da', '83018530-f182-4734-afc2-cf4ecc96802d', '33333333-cccc-dddd-eeee-333333333333', 3, (TIMESTAMP '2025-05-16' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), NULL, NULL)
ON CONFLICT DO NOTHING;

---- 17. 訂單大項目資料 "orders"
INSERT INTO orders (order_id, user_id, address, phone, payment_type, discount_type, payment_status, total_price, discount_price) VALUES
('c62e3ad6-19cc-4b58-bec7-231f41b678ac', 'b2c3d4e5-f678-90ab-cdef-234567890abc', '高雄市鼓山區美術館路45號', '0912345678', 'credit_card', 'none', 0, 3576.74, 794.83),
('58fcd7d9-62ee-4bbd-bfcd-086044ba4060', 'c3d4e5f6-7890-abcd-ef12-34567890abcd', '台中市西區公益路321巷9號', '0987654321', 'credit_card', 'none', 1, 6482.73, 439.63),
('f4977608-2efb-4725-94bc-b3265440b4c5', 'c3d4e5f6-7890-abcd-ef12-34567890abcd', '台北市中山區南京東路3段123號', '0978123456', 'atm', 'none', 0, 1610.73, 436.75),
('8c1e4f18-841e-49de-bc5e-c6754473f929', 'b2c3d4e5-f678-90ab-cdef-234567890abc', '台北市中山區南京東路3段123號', '0912345678', 'cvs', 'earlybird', 0, 5769.06, 839.86),
('8426dbe1-70cd-431c-b87a-5530a4d99a06', 'a1b2c3d4-e5f6-7890-abcd-ef1234567890', '台北市中山區南京東路3段123號', '0987654321', 'credit_card', 'none', 0, 6263.64, 596.12)
ON CONFLICT DO NOTHING;


---- 18. 訂單細項資料 "order_item"
INSERT INTO order_item (order_item_id, order_id, tour_id, total_price, discount_price, payment_status, quantity, start_date, end_date, room_type) VALUES
('cac34fe5-c619-49dc-8cdd-79509e02f20b', 'c62e3ad6-19cc-4b58-bec7-231f41b678ac', '99999999-cccc-dddd-eeee-999999999999', 4500, 3800, 1, 2, (TIMESTAMP '2025-05-18' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), NULL, NULL),
('f3d2d83e-f782-41dc-8e52-0b49a2cfce0d', '58fcd7d9-62ee-4bbd-bfcd-086044ba4060', '22222222-bbbb-cccc-dddd-222222222222', 5500, 2000, 2, 3, (TIMESTAMP '2025-11-10' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), (TIMESTAMP '2025-11-15' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), NULL),
('d19eaf9b-cef7-4053-b807-e54532b86dd0', 'f4977608-2efb-4725-94bc-b3265440b4c5', '11111111-aaaa-bbbb-cccc-111111111111', 1200, 800, 3, 1, (TIMESTAMP '2025-12-01' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), (TIMESTAMP '2025-12-05' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), NULL),
('31ff7da9-f987-426b-b0bd-f5a03c5d9d9a', '8c1e4f18-841e-49de-bc5e-c6754473f929', '88888888-bbbb-cccc-dddd-888888888888', 7000, NULL, 1, 4, (TIMESTAMP '2025-05-19' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), (TIMESTAMP '2025-05-20' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), '豪華家庭房'),
('5739fb80-cd14-43ac-91c8-da6c132238b5', '58fcd7d9-62ee-4bbd-bfcd-086044ba4060', '44444444-dddd-eeee-ffff-444444444444', 8400, NULL, 1, 3, (TIMESTAMP '2025-05-15' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), (TIMESTAMP '2025-05-16' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), NULL),
('36a2abc9-dd5f-4ff4-8f1f-29f70067655e', 'c62e3ad6-19cc-4b58-bec7-231f41b678ac', '66666666-ffff-aaaa-bbbb-666666666666', 4900, 4000, 3, 5, (TIMESTAMP '2025-10-15' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), (TIMESTAMP '2025-10-22' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), NULL),
('363eaf2c-772f-4b71-bc1c-132454d3c212', '8c1e4f18-841e-49de-bc5e-c6754473f929', '55555555-eeee-ffff-aaaa-555555555555', 8800, NULL, 1, 2, (TIMESTAMP '2025-05-14' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), (TIMESTAMP '2025-05-15' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), '設計雙人房'),
('0adab552-7e49-412d-9ca7-dbd7cf455f7f', 'c62e3ad6-19cc-4b58-bec7-231f41b678ac', '00000000-dddd-eeee-ffff-000000000000', 4800, 3500, 1, 3, (TIMESTAMP '2025-11-05' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), (TIMESTAMP '2025-11-15' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), NULL),
('e6b85926-697a-4a79-9d6a-b87de5f5819e', 'f4977608-2efb-4725-94bc-b3265440b4c5', '77777777-aaaa-bbbb-cccc-777777777777', 7700, 7000, 1, 2, (TIMESTAMP '2025-05-13' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), (TIMESTAMP '2025-05-14' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), NULL),
('5c8096e9-9771-4b1a-982c-d6c5fed5521c', '8426dbe1-70cd-431c-b87a-5530a4d99a06', '33333333-cccc-dddd-eeee-333333333333', 6900, NULL, 3, 3, (TIMESTAMP '2025-05-16' + (CURRENT_DATE - DATE '2025-05-20') * INTERVAL '1 day'), NULL, NULL)
ON CONFLICT DO NOTHING;

---- 19. 付款紀錄資料 "payment"

---- 20. 評論資料 "review"
INSERT INTO "review" (
    review_id, user_id, tour_id, type, hashtag, rating, content, created_at, updated_at
) VALUES
('37111743-9a58-56ca-be59-beb8aedf3c12', 'a1b2c3d4-e5f6-7890-abcd-ef1234567890', NULL, 'web', '#操作直覺', 5, '整個網站設計非常友善，喜歡！', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('b284a294-e9ed-5727-b431-1ec989c1e1d4', 'b2c3d4e5-f678-90ab-cdef-234567890abc', NULL, 'web', '#速度很快', 4, '下單流程簡單又快速，推薦。', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('bdb47d6c-f31e-5b50-821c-dea0b07f9c19', 'c3d4e5f6-7890-abcd-ef12-34567890abcd', '00000000-dddd-eeee-ffff-000000000000', 'travel', NULL, 5, '北海道行程安排完美，超值！', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('fdca8955-aacc-503c-89b2-dbf35519cc83', 'a1b2c3d4-e5f6-7890-abcd-ef1234567890', '11111111-aaaa-bbbb-cccc-111111111111', 'travel', NULL, 4, '巴黎巡禮浪漫又美麗！', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('1259e4c1-3797-5a48-8c82-f22cba8be4e2', 'b2c3d4e5-f678-90ab-cdef-234567890abc', '22222222-bbbb-cccc-dddd-222222222222', 'hotel', NULL, 5, '飯店地點方便，乾淨舒適。', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('e29fe3c7-aab3-5492-bf56-f7e0f0440b95', 'c3d4e5f6-7890-abcd-ef12-34567890abcd', '33333333-cccc-dddd-eeee-333333333333', 'hotel', NULL, 4, '設施不錯但早餐普通。', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('d66dabde-43c6-5e81-932b-3915dd10b0ca', 'a1b2c3d4-e5f6-7890-abcd-ef1234567890', '44444444-dddd-eeee-ffff-444444444444', 'food', NULL, 5, '曼谷美食超級好吃，值得一試！', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('dde9a13f-ade0-57f1-86d7-8c5b9fb23bd0', 'b2c3d4e5-f678-90ab-cdef-234567890abc', '55555555-eeee-ffff-aaaa-555555555555', 'food', NULL, 3, '有些小吃偏油但整體好吃。', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('eab365ba-b494-506b-847b-93d8be4b8b3d', 'c3d4e5f6-7890-abcd-ef12-34567890abcd', '66666666-ffff-aaaa-bbbb-666666666666', 'spot', NULL, 5, '景色壯觀，很值得一遊！', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('3860c110-61ce-5e9f-bb8e-5e6e6f18596b', 'a1b2c3d4-e5f6-7890-abcd-ef1234567890', '77777777-aaaa-bbbb-cccc-777777777777', 'spot', NULL, 4, '景點人潮多但風景超美。', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
ON CONFLICT DO NOTHING;

---- 21. 隱藏玩法資料 "hidden_play"
INSERT INTO "hidden_play" (
    hidden_play_id, user_id, tour_id, title, content, share_url, created_at, updated_at
) VALUES
('8e1bf4f4-134f-59ed-a95f-0da1da059922', 'a1b2c3d4-e5f6-7890-abcd-ef1234567890', '00000000-dddd-eeee-ffff-000000000000', '北海道隱藏雪景', '小巷裡的冰雕展超夢幻，遊客很少！', 'http://localhost:3000/uploads/seed/hidden.svg', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('fc8e31fc-eb24-59b7-a1e4-4ae49d7052f4', 'b2c3d4e5-f678-90ab-cdef-234567890abc', '11111111-aaaa-bbbb-cccc-111111111111', '巴黎秘境咖啡廳', '塞納河旁的小咖啡廳，超有文青感。', 'http://localhost:3000/uploads/seed/hidden.svg', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('24e6cf8b-9917-54c5-9288-00bd4175ee25', 'c3d4e5f6-7890-abcd-ef12-34567890abcd', '22222222-bbbb-cccc-dddd-222222222222', '隱藏版清邁夜市', '本地人推薦的夜市小吃，便宜又好吃。', 'http://localhost:3000/uploads/seed/hidden.svg', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('5b5f9910-9e68-560f-bd2b-0d43773350d2', 'a1b2c3d4-e5f6-7890-abcd-ef1234567890', '33333333-cccc-dddd-eeee-333333333333', '秘密海灘', '搭乘小船才能到達的超夢幻海灘。', 'http://localhost:3000/uploads/seed/hidden.svg', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('a46aa767-cee6-5b8c-8a64-17cc8072669e', 'b2c3d4e5-f678-90ab-cdef-234567890abc', '44444444-dddd-eeee-ffff-444444444444', '曼谷隱藏美食街', '巷弄內隱藏的米其林推薦小吃。', 'http://localhost:3000/uploads/seed/hidden.svg', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('f6fa7323-3bc9-574d-953b-305504d3390b', 'c3d4e5f6-7890-abcd-ef12-34567890abcd', '55555555-eeee-ffff-aaaa-555555555555', '紐約市秘密書店', '藏身公園旁的獨立書店，超有味道。', 'http://localhost:3000/uploads/seed/hidden.svg', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
ON CONFLICT DO NOTHING;

---- 22. 自動設定資料 "auto_setting"
INSERT INTO "auto_setting" (
    auto_setting_id, user_id, early_notify, flexible_notify, country, region, price, created_at, updated_at
) VALUES
(
    '1111aaaa-2222-bbbb-3333-cccc4444dddd',
    'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
    0,
    1,
    'Japan',
    'Tokyo',
    1200.5,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
),
(
    '2222bbbb-3333-cccc-4444-dddd5555eeee',
    'b2c3d4e5-f678-90ab-cdef-234567890abc',
    0,
    0,
    NULL,
    NULL,
    NULL,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
),
(
    '3333cccc-4444-dddd-5555-eeee6666ffff',
    'c3d4e5f6-7890-abcd-ef12-34567890abcd',
    1,
    1,
    'France',
    'Paris',
    1850.75,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
),
(
    '4444dddd-5555-eeee-6666-ffff7777aaaa',
    'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
    1,
    0,
    NULL,
    NULL,
    NULL,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
)
ON CONFLICT DO NOTHING;

---- 23. 使用者收藏旅遊商品 "favorite"
INSERT INTO "favorite" (
    favorite_id, user_id, tour_id, created_at, updated_at
) VALUES
('619b2664-e188-546f-8368-934d4a81d166', 'a1b2c3d4-e5f6-7890-abcd-ef1234567890', '00000000-dddd-eeee-ffff-000000000000', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('fa32654d-66eb-5b2d-8e29-cf6d8199cd54', 'b2c3d4e5-f678-90ab-cdef-234567890abc', '11111111-aaaa-bbbb-cccc-111111111111', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('3e51f707-43e2-5855-b9e1-0fa379c26d97', 'c3d4e5f6-7890-abcd-ef12-34567890abcd', '22222222-bbbb-cccc-dddd-222222222222', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('10af503a-8b64-548d-aa06-6adbecb198ee', 'a1b2c3d4-e5f6-7890-abcd-ef1234567890', '22222222-bbbb-cccc-dddd-222222222222', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('ea545877-b0be-5f33-9c49-107374a8f8ff', 'a1b2c3d4-e5f6-7890-abcd-ef1234567890', '33333333-cccc-dddd-eeee-333333333333', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('a89119d7-7f3c-5894-9b7b-9ea2b73853ac', 'b2c3d4e5-f678-90ab-cdef-234567890abc', '44444444-dddd-eeee-ffff-444444444444', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('c4a50a4b-7f8a-5d20-967d-0c63e2af1e96', 'c3d4e5f6-7890-abcd-ef12-34567890abcd', '55555555-eeee-ffff-aaaa-555555555555', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
ON CONFLICT DO NOTHING;


---- 24. 會員旅遊積分資料 "point_record"
INSERT INTO point_record (point_id, user_id, order_id, type, point) VALUES
('a2e85047-514d-486e-ba0e-b41adf788ea3', 'c3d4e5f6-7890-abcd-ef12-34567890abcd', 'f4977608-2efb-4725-94bc-b3265440b4c5', '新增', 1610),
('3c9e2b67-1478-4669-adeb-a5bef809d537', 'c3d4e5f6-7890-abcd-ef12-34567890abcd', 'f4977608-2efb-4725-94bc-b3265440b4c5', '減少', -436)
ON CONFLICT DO NOTHING;


---- 25. 優惠卷與使用者綁定的資料 "user_coupon"
INSERT INTO "user_coupon" (
    user_coupon_id, user_id, order_id, coupon_id, status
) VALUES
('6f610e1c-51cf-4709-b8e2-5b8b96751100', 'b2c3d4e5-f678-90ab-cdef-234567890abc', 'c62e3ad6-19cc-4b58-bec7-231f41b678ac', '33333333-cccc-dddd-eeee-333333333333', 1),
('079a19f1-679d-4282-b047-e57d40b473f8', 'c3d4e5f6-7890-abcd-ef12-34567890abcd', NULL, '33333333-cccc-dddd-eeee-333333333333', 0),
('870df12e-1ec6-49da-8f91-3ffefb4ca8b0', 'b2c3d4e5-f678-90ab-cdef-234567890abc', '8c1e4f18-841e-49de-bc5e-c6754473f929', '44444444-dddd-eeee-ffff-444444444444', 1),
('4b202c03-9bde-4c8c-9c03-f23aac550c03', 'a1b2c3d4-e5f6-7890-abcd-ef1234567890', '8426dbe1-70cd-431c-b87a-5530a4d99a06', '44444444-dddd-eeee-ffff-444444444444', 1)
ON CONFLICT DO NOTHING;
