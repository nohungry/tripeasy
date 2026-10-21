/* ------------------ 刪除假資料 -----------------------  */

delete from user_coupon;
delete from point_record;
delete from order_item;
delete from orders;
delete from cart_item;
delete from cart;
delete from hidden_play;
delete from review ;
delete from region;
delete from country;
delete from notification;
delete from hotel_room;
delete from hotel;
delete from restaurant_business;
delete from restaurant_menu;
delete from restaurant;
delete from tour_detail;
delete from favorite;
delete from auto_setting;
delete from coupon;
delete from user_level;
delete from "socialLogin";
delete from "user" ;
delete from tour;

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
    'user',
    '$2b$10$abcd1234abcd1234abcd12', 
    0,
    NULL,
    'https://example.com/avatar/alice.jpg',
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
    '$2b$10$efgh5678efgh5678efgh56',
    1,
    NULL,
    'https://example.com/avatar/bob.jpg',
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
    'user',
    '$2b$10$ijkl9012ijkl9012ijkl90',
    NULL,
    NULL,
    NULL,
    3,
    2,
    1,
    3,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);

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
);

---- 3. 會員等級資料 "user_level"
INSERT INTO "user_level" (
    level_id, user_id, level, name, badge_url, travel_point, benefits, created_at, updated_at
) VALUES
(
    'd4e5f678-90ab-cdef-1234-567890abcdef',
    'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
    'Level 3',
    'Explorer',
    'https://example.com/badges/explorer.png',
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
    'https://example.com/badges/adventure_master.png',
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
    'https://example.com/badges/rookie_traveler.png',
    800,
    'Priority customer support; Welcome gift',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);

---- 4. 優惠卷資料 "coupon"
INSERT INTO "coupon" (
    coupon_id, code, discount, description, expire_date, created_at, updated_at
) VALUES
(
    '11111111-aaaa-bbbb-cccc-111111111111',
    'WELCOME100',
    100.0,
    '首次註冊禮，折抵新台幣 100 元',
    '2025-12-31 23:59:59',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
),
(
    '22222222-bbbb-cccc-dddd-222222222222',
    'SUMMER50',
    50.0,
    '夏日旅遊季，折抵新台幣 50 元',
    '2025-08-31 23:59:59',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
),
(
    '33333333-cccc-dddd-eeee-333333333333',
    'TRAVEL10P',
    10.0,
    '旅遊商品 10% 折扣 (最高折抵 500 元)',
    '2025-09-30 23:59:59',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
),
(
    '44444444-dddd-eeee-ffff-444444444444',
    'VIP300',
    300.0,
    '尊榮會員專屬，折抵新台幣 300 元',
    '2025-12-31 23:59:59',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
),
(
    '55555555-eeee-ffff-aaaa-555555555555',
    'SPRING20',
    20.0,
    '春季限定，旅遊折抵新台幣 20 元',
    '2025-05-31 23:59:59',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);

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
    '2025-12-01 00:00:00', '2025-12-05 23:59:59', 5, 45000,
    'Japan', 'Hokkaido', '札幌市中央區南1條西2丁目',
    'https://goo.gl/maps/hokkaido1', 'https://calendar.google.com/event?hokkaido1',
    1, 2, 3,
    '請攜帶防寒衣物。', '探索北海道最美雪景與溫泉之旅。',
    'https://example.com/images/cover1.jpg',
    'https://example.com/images/1-1.jpg', '札幌夜景',
    'https://example.com/images/1-2.jpg', '小樽運河',
    'https://example.com/images/1-3.jpg', '登別溫泉',
    'https://example.com/images/1-4.jpg', '旭川動物園',
    'https://example.com/images/1-5.jpg', '富良野薰衣草',
    'https://example.com/images/1-6.jpg', '冰雪祭典',
    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
),
-- tourgroup: travel
(
    '22222222-bbbb-cccc-dddd-222222222222',
    'tourgroup', 'travel', 1,
    '馬爾地夫蜜月天堂 6 日', '享受專屬你的藍色海洋假期',
    '2025-11-10 00:00:00', '2025-11-15 23:59:59', 6, 98000,
    'Maldives', 'Male', '北馬列環礁私人島嶼',
    'https://goo.gl/maps/maldives1', 'https://calendar.google.com/event?maldives1',
    2, 1, 3,
    '請攜帶防曬用品。', '入住水上別墅，專屬浪漫行程。',
    'https://example.com/images/cover2.jpg',
    'https://example.com/images/2-1.jpg', '水上別墅景色',
    'https://example.com/images/2-2.jpg', '海上活動',
    'https://example.com/images/2-3.jpg', '私人沙灘',
    'https://example.com/images/2-4.jpg', '環礁浮潛',
    'https://example.com/images/2-5.jpg', 'SPA中心',
    'https://example.com/images/2-6.jpg', '夕陽巡航',
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
    'https://example.com/images/cover3.jpg',
    'https://example.com/images/3-1.jpg', '章魚燒',
    'https://example.com/images/3-2.jpg', '燒肉體驗',
    'https://example.com/images/3-3.jpg', '居酒屋文化',
    'https://example.com/images/3-4.jpg', '大阪壽司',
    'https://example.com/images/3-5.jpg', '道頓堀夜景',
    'https://example.com/images/3-6.jpg', '黑門市場',
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
    'https://example.com/images/cover4.jpg',
    'https://example.com/images/4-1.jpg', '巴黎聖母院',
    'https://example.com/images/4-2.jpg', '盧森堡公園',
    'https://example.com/images/4-3.jpg', '羅丹美術館',
    'https://example.com/images/4-4.jpg', '先賢祠',
    'https://example.com/images/4-5.jpg', '拉丁區書店',
    'https://example.com/images/4-6.jpg', '塞納河畔',
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
    'https://example.com/images/cover5.jpg',
    'https://example.com/images/5-1.jpg', '曼谷設計旅館',
    'https://example.com/images/5-2.jpg', '夜市巡禮',
    'https://example.com/images/5-3.jpg', '昭披耶河景',
    'https://example.com/images/5-4.jpg', '大皇宮一日遊',
    'https://example.com/images/5-5.jpg', '文青咖啡店',
    'https://example.com/images/5-6.jpg', '市集探險',
    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
),
-- tourgroup: travel
(
    '66666666-ffff-aaaa-bbbb-666666666666',
    'tourgroup', 'travel', 1,
    '義大利深度文化之旅', '在藝術與美食中迷失',
    '2025-10-15 00:00:00', '2025-10-22 23:59:59', 8, 72000,
    'Italy', 'Rome', '羅馬市中心西班牙廣場',
    'https://goo.gl/maps/rome1', 'https://calendar.google.com/event?rome1',
    1, 2, 3,
    '行程部分需攀爬古蹟階梯。', '穿越千年歷史，體驗義式浪漫。',
    'https://example.com/images/cover6.jpg',
    'https://example.com/images/6-1.jpg', '羅馬競技場',
    'https://example.com/images/6-2.jpg', '聖彼得大教堂',
    'https://example.com/images/6-3.jpg', '特雷維噴泉',
    'https://example.com/images/6-4.jpg', '西班牙階梯',
    'https://example.com/images/6-5.jpg', '梵蒂岡博物館',
    'https://example.com/images/6-6.jpg', '羅馬廣場',
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
    'https://example.com/images/cover7.jpg',
    'https://example.com/images/7-1.jpg', '延南洞文青街',
    'https://example.com/images/7-2.jpg', '首爾森林',
    'https://example.com/images/7-3.jpg', '聖水洞咖啡店',
    'https://example.com/images/7-4.jpg', '弘大藝術牆',
    'https://example.com/images/7-5.jpg', '城東區手作市集',
    'https://example.com/images/7-6.jpg', '夜市甜品巡禮',
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
    'https://example.com/images/cover8.jpg',
    'https://example.com/images/8-1.jpg', '清邁古城',
    'https://example.com/images/8-2.jpg', '素貼山夜景',
    'https://example.com/images/8-3.jpg', '瓦洛洛市場',
    'https://example.com/images/8-4.jpg', '寧曼路商圈',
    'https://example.com/images/8-5.jpg', '周六市集',
    'https://example.com/images/8-6.jpg', '寺廟文化探索',
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
    'https://example.com/images/cover9.jpg',
    'https://example.com/images/9-1.jpg', '六合夜市美食',
    'https://example.com/images/9-2.jpg', '瑞豐夜市人氣小吃',
    'https://example.com/images/9-3.jpg', '旗津海鮮街',
    'https://example.com/images/9-4.jpg', '新崛江甜品',
    'https://example.com/images/9-5.jpg', '鹽埕區老店',
    'https://example.com/images/9-6.jpg', '高雄港夜景',
    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
),
-- tourgroup: travel
(
    '00000000-dddd-eeee-ffff-000000000000',
    'tourgroup', 'travel', 1,
    '紐西蘭壯麗景觀自駕遊', '開啟最自由的冒險',
    '2025-11-05 00:00:00', '2025-11-15 23:59:59', 11, 85000,
    'New Zealand', 'South Island', '基督城市中心',
    'https://goo.gl/maps/nz1', 'https://calendar.google.com/event?nz1',
    3, 1, 2,
    '請攜帶國際駕照並確保駕駛經驗。', '從冰河到峽灣，體驗純粹自然。',
    'https://example.com/images/cover10.jpg',
    'https://example.com/images/10-1.jpg', '庫克山冰川',
    'https://example.com/images/10-2.jpg', '皇后鎮湖光山色',
    'https://example.com/images/10-3.jpg', '米佛峽灣巡航',
    'https://example.com/images/10-4.jpg', '蒂卡波湖星空',
    'https://example.com/images/10-5.jpg', '箭鎮金礦小鎮',
    'https://example.com/images/10-6.jpg', '瓦納卡湖',
    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
);

---- 6. 旅遊產品細項資料 "tour_detail"
INSERT INTO "tour_detail" (
    tour_detail_id, tour_id, feature_img1, feature_desc1, feature_img2, feature_desc2, feature_img3, feature_desc3, itinerary, created_at, updated_at
) VALUES
(
    'aaa11111-bbbb-2222-cccc-3333dddd4444',
    '11111111-aaaa-bbbb-cccc-111111111111',
    'https://example.com/feature/hokkaido1.jpg', '旭川雪祭典體驗',
    'https://example.com/feature/hokkaido2.jpg', '美瑛白金青池探訪',
    'https://example.com/feature/hokkaido3.jpg', '登別地獄谷探險',
    'Day1: 札幌市區巡禮,Day2: 小樽運河,Day3: 美瑛青池,Day4: 登別溫泉,Day5: 旭川雪祭',
    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
),
(
    'bbb22222-cccc-3333-dddd-4444eeee5555',
    '22222222-bbbb-cccc-dddd-222222222222',
    'https://example.com/feature/maldives1.jpg', '水上別墅享受',
    'https://example.com/feature/maldives2.jpg', '私人島嶼浮潛',
    'https://example.com/feature/maldives3.jpg', '夕陽巡航浪漫',
    'Day1: 抵達馬列,Day2: 私人島浮潛,Day3: SPA與日光浴,Day4: 水上別墅活動,Day5: 浪漫晚宴,Day6: 自由活動',
    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
),
(
    'ccc33333-dddd-4444-eeee-5555ffff6666',
    '66666666-ffff-aaaa-bbbb-666666666666',
    'https://example.com/feature/italy1.jpg', '羅馬競技場探訪',
    'https://example.com/feature/italy2.jpg', '托斯卡尼鄉村漫遊',
    'https://example.com/feature/italy3.jpg', '梵蒂岡藝術之旅',
    'Day1: 羅馬市區巡禮,Day2: 梵蒂岡博物館,Day3: 羅馬古城,Day4: 托斯卡尼自由行,Day5: 比薩斜塔,Day6: 佛羅倫斯藝術街區,Day7: 羅馬購物日,Day8: 返回',
    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
),
(
    'ddd44444-eeee-5555-ffff-6666aaaa7777',
    '00000000-dddd-eeee-ffff-000000000000',
    'https://example.com/feature/nz1.jpg', '庫克山冰河健行',
    'https://example.com/feature/nz2.jpg', '蒂卡波星空夜拍',
    'https://example.com/feature/nz3.jpg', '米佛峽灣巡航體驗',
    'Day1: 基督城市區探索,Day2: 蒂卡波湖星空,Day3: 庫克山健行,Day4: 皇后鎮自由行,Day5: 米佛峽灣巡航,Day6: 弗朗茲約瑟夫冰河健行,Day7-11: 南島深度自由探索',
    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
),
(
    'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
    '44444444-dddd-eeee-ffff-444444444444',
    'https://example.com/feature/paris1.jpg', '巴黎聖母院巡禮',
    'https://example.com/feature/paris2.jpg', '塞納河畔夜遊',
    'https://example.com/feature/paris3.jpg', '拉丁區藝術巷弄',
    'Day1: 巴黎聖母院參觀,Day2: 塞納河遊船,Day3: 拉丁區文學之旅',
    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
),
(
    'b2c3d4e5-f678-90ab-cdef-234567890abc',
    '77777777-aaaa-bbbb-cccc-777777777777',
    'https://example.com/feature/seoul1.jpg', '延南洞文青街探訪',
    'https://example.com/feature/seoul2.jpg', '聖水洞咖啡巡禮',
    'https://example.com/feature/seoul3.jpg', '弘大街頭藝術欣賞',
    'Day1: 延南洞文青咖啡館巡禮,Day2: 聖水洞手作街探險,Day3: 弘大夜市與藝術街探索',
    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
);

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
);

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
;

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
('66666666-ffff-aaaa-bbbb-666666666666', 'bbb22222-cccc-3333-dddd-4444eeee5555', '木瓜牛奶', 70.0, '高雄人氣飲品，清甜滑順解渴。', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

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
);

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
    'https://example.com/images/hotel_bangkok_room1.jpg',
    '現代簡約風格，附舒適大床與書桌。',
    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
),
(
    'aaa11111-bbbb-3333-cccc-4444dddd5555',
    '11111111-aaaa-bbbb-cccc-111111111111',
    '豪華家庭房',
    4,
    5,
    'https://example.com/images/hotel_bangkok_room2.jpg',
    '寬敞空間，適合親子同住，附沙發床。',
    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
),
(
    'bbb22222-cccc-4444-dddd-5555eeee6666',
    '22222222-bbbb-cccc-dddd-222222222222',
    '自然雙人房',
    2,
    8,
    'https://example.com/images/hotel_chiangmai_room1.jpg',
    '溫暖木質設計，大面窗採光。',
    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
),
(
    'bbb22222-cccc-5555-dddd-6666eeee7777',
    '22222222-bbbb-cccc-dddd-222222222222',
    '親子套房',
    4,
    6,
    'https://example.com/images/hotel_chiangmai_room2.jpg',
    '親子專用設施，兒童遊戲空間。',
    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
);

---- 12. 重要通知資料(促銷/異動) "notification"
INSERT INTO "notification" (
    notification_id, tour_id, type, start_date, end_date, discount, promo_price, change_desc, created_at, updated_at
) VALUES
(
    '11111111-aaaa-bbbb-cccc-111111111111',
    '11111111-aaaa-bbbb-cccc-111111111111',  -- 北海道雪景
    '促銷',
    '2025-11-01 00:00:00',
    '2025-11-30 23:59:59',
    10.0,
    40500.0,
    NULL,
    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
),
(
    '22222222-bbbb-cccc-dddd-222222222222',
    '22222222-bbbb-cccc-dddd-222222222222',  -- 馬爾地夫蜜月
    '促銷',
    '2025-10-01 00:00:00',
    '2025-10-31 23:59:59',
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
);

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
('aaaaaaa3-dddd-eeee-ffff-aaaaaaa3aaaa', '南非', CURRENT_TIMESTAMP);

---- 14. 地區資料 "region"
INSERT INTO "region" (region_id, country_id, name, created_at) VALUES
(uuid_generate_v4(), '11111111-1111-1111-1111-111111111111', '台北市', CURRENT_TIMESTAMP),
(uuid_generate_v4(), '11111111-1111-1111-1111-111111111111', '新北市', CURRENT_TIMESTAMP),
(uuid_generate_v4(), '11111111-1111-1111-1111-111111111111', '桃園市', CURRENT_TIMESTAMP),
(uuid_generate_v4(), '11111111-1111-1111-1111-111111111111', '台中市', CURRENT_TIMESTAMP),
(uuid_generate_v4(), '11111111-1111-1111-1111-111111111111', '台南市', CURRENT_TIMESTAMP),
(uuid_generate_v4(), '11111111-1111-1111-1111-111111111111', '高雄市', CURRENT_TIMESTAMP),
(uuid_generate_v4(), '11111111-1111-1111-1111-111111111111', '基隆市', CURRENT_TIMESTAMP),
(uuid_generate_v4(), '11111111-1111-1111-1111-111111111111', '新竹市', CURRENT_TIMESTAMP),
(uuid_generate_v4(), '11111111-1111-1111-1111-111111111111', '新竹縣', CURRENT_TIMESTAMP),
(uuid_generate_v4(), '11111111-1111-1111-1111-111111111111', '苗栗縣', CURRENT_TIMESTAMP),
(uuid_generate_v4(), '11111111-1111-1111-1111-111111111111', '彰化縣', CURRENT_TIMESTAMP),
(uuid_generate_v4(), '11111111-1111-1111-1111-111111111111', '南投縣', CURRENT_TIMESTAMP),
(uuid_generate_v4(), '11111111-1111-1111-1111-111111111111', '雲林縣', CURRENT_TIMESTAMP),
(uuid_generate_v4(), '11111111-1111-1111-1111-111111111111', '嘉義市', CURRENT_TIMESTAMP),
(uuid_generate_v4(), '11111111-1111-1111-1111-111111111111', '嘉義縣', CURRENT_TIMESTAMP),
(uuid_generate_v4(), '11111111-1111-1111-1111-111111111111', '屏東縣', CURRENT_TIMESTAMP),
(uuid_generate_v4(), '11111111-1111-1111-1111-111111111111', '宜蘭縣', CURRENT_TIMESTAMP),
(uuid_generate_v4(), '11111111-1111-1111-1111-111111111111', '花蓮縣', CURRENT_TIMESTAMP),
(uuid_generate_v4(), '11111111-1111-1111-1111-111111111111', '台東縣', CURRENT_TIMESTAMP),
(uuid_generate_v4(), '11111111-1111-1111-1111-111111111111', '澎湖縣', CURRENT_TIMESTAMP),
(uuid_generate_v4(), '11111111-1111-1111-1111-111111111111', '金門縣', CURRENT_TIMESTAMP),
(uuid_generate_v4(), '11111111-1111-1111-1111-111111111111', '連江縣', CURRENT_TIMESTAMP),
(uuid_generate_v4(), '22222222-2222-2222-2222-222222222222', '東京', CURRENT_TIMESTAMP),
(uuid_generate_v4(), '22222222-2222-2222-2222-222222222222', '大阪', CURRENT_TIMESTAMP),
(uuid_generate_v4(), '22222222-2222-2222-2222-222222222222', '京都', CURRENT_TIMESTAMP),
(uuid_generate_v4(), '22222222-2222-2222-2222-222222222222', '北海道', CURRENT_TIMESTAMP),
(uuid_generate_v4(), '22222222-2222-2222-2222-222222222222', '沖繩', CURRENT_TIMESTAMP),
(uuid_generate_v4(), '33333333-3333-3333-3333-333333333333', '首爾', CURRENT_TIMESTAMP),
(uuid_generate_v4(), '33333333-3333-3333-3333-333333333333', '釜山', CURRENT_TIMESTAMP),
(uuid_generate_v4(), '33333333-3333-3333-3333-333333333333', '濟州島', CURRENT_TIMESTAMP),
(uuid_generate_v4(), '44444444-4444-4444-4444-444444444444', '香港島', CURRENT_TIMESTAMP),
(uuid_generate_v4(), '44444444-4444-4444-4444-444444444444', '九龍', CURRENT_TIMESTAMP),
(uuid_generate_v4(), '44444444-4444-4444-4444-444444444444', '新界', CURRENT_TIMESTAMP),
(uuid_generate_v4(), '55555555-5555-5555-5555-555555555555', '澳門半島', CURRENT_TIMESTAMP),
(uuid_generate_v4(), '55555555-5555-5555-5555-555555555555', '氹仔', CURRENT_TIMESTAMP),
(uuid_generate_v4(), '55555555-5555-5555-5555-555555555555', '路氹城', CURRENT_TIMESTAMP),
(uuid_generate_v4(), '66666666-6666-6666-6666-666666666666', '北京', CURRENT_TIMESTAMP),
(uuid_generate_v4(), '66666666-6666-6666-6666-666666666666', '上海', CURRENT_TIMESTAMP),
(uuid_generate_v4(), '66666666-6666-6666-6666-666666666666', '廣州', CURRENT_TIMESTAMP),
(uuid_generate_v4(), '66666666-6666-6666-6666-666666666666', '成都', CURRENT_TIMESTAMP),
(uuid_generate_v4(), '66666666-6666-6666-6666-666666666666', '西安', CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'ddddddd4-aaaa-bbbb-cccc-ddddddd4dddd', '紐約', CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'ddddddd4-aaaa-bbbb-cccc-ddddddd4dddd', '洛杉磯', CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'ddddddd4-aaaa-bbbb-cccc-ddddddd4dddd', '舊金山', CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'ddddddd4-aaaa-bbbb-cccc-ddddddd4dddd', '拉斯維加斯', CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'ddddddd4-aaaa-bbbb-cccc-ddddddd4dddd', '夏威夷', CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee', '倫敦', CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee', '曼徹斯特', CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee', '愛丁堡', CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'ffffffff-ffff-ffff-ffff-ffffffffffff', '巴黎', CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'ffffffff-ffff-ffff-ffff-ffffffffffff', '里昂', CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'ffffffff-ffff-ffff-ffff-ffffffffffff', '尼斯', CURRENT_TIMESTAMP),
(uuid_generate_v4(), '77777777-7777-7777-7777-777777777777', '曼谷', CURRENT_TIMESTAMP),
(uuid_generate_v4(), '77777777-7777-7777-7777-777777777777', '清邁', CURRENT_TIMESTAMP),
(uuid_generate_v4(), '77777777-7777-7777-7777-777777777777', '普吉島', CURRENT_TIMESTAMP),
(uuid_generate_v4(), '77777777-7777-7777-7777-777777777777', '芭達雅', CURRENT_TIMESTAMP),
(uuid_generate_v4(), '88888888-8888-8888-8888-888888888888', '胡志明市', CURRENT_TIMESTAMP),
(uuid_generate_v4(), '88888888-8888-8888-8888-888888888888', '河內', CURRENT_TIMESTAMP),
(uuid_generate_v4(), '88888888-8888-8888-8888-888888888888', '峴港', CURRENT_TIMESTAMP),
(uuid_generate_v4(), '99999999-9999-9999-9999-999999999999', '新加坡', CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', '吉隆坡', CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', '檳城', CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', '沙巴', CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', '峇里島', CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', '雅加達', CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'cccccccc-cccc-cccc-cccc-cccccccccccc', '馬尼拉', CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'cccccccc-cccc-cccc-cccc-cccccccccccc', '宿霧', CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'cccccccc-cccc-cccc-cccc-cccccccccccc', '長灘島', CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'dddddddd-dddd-dddd-dddd-dddddddddddd', '德里', CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'dddddddd-dddd-dddd-dddd-dddddddddddd', '孟買', CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'dddddddd-dddd-dddd-dddd-dddddddddddd', '齋浦爾', CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'bbbbbbb8-eeee-ffff-aaaa-bbbbbbb8bbbb', '雪梨', CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'bbbbbbb8-eeee-ffff-aaaa-bbbbbbb8bbbb', '墨爾本', CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'bbbbbbb8-eeee-ffff-aaaa-bbbbbbb8bbbb', '布里斯本', CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'bbbbbbb8-eeee-ffff-aaaa-bbbbbbb8bbbb', '黃金海岸', CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'ccccccc9-ffff-aaaa-bbbb-ccccccc9cccc', '奧克蘭', CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'ccccccc9-ffff-aaaa-bbbb-ccccccc9cccc', '皇后鎮', CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'ccccccc9-ffff-aaaa-bbbb-ccccccc9cccc', '基督城', CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'ddddddd0-aaaa-bbbb-cccc-ddddddd0dddd', '杜拜', CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'ddddddd0-aaaa-bbbb-cccc-ddddddd0dddd', '阿布達比', CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'eeeeeee1-bbbb-cccc-dddd-eeeeeee1eeee', '伊斯坦堡', CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'eeeeeee1-bbbb-cccc-dddd-eeeeeee1eeee', '卡帕多奇亞', CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'eeeeeee1-bbbb-cccc-dddd-eeeeeee1eeee', '安塔利亞', CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'fffffff2-cccc-dddd-eeee-fffffff2ffff', '開羅', CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'fffffff2-cccc-dddd-eeee-fffffff2ffff', '盧克索', CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'aaaaaaa3-dddd-eeee-ffff-aaaaaaa3aaaa', '開普敦', CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'aaaaaaa3-dddd-eeee-ffff-aaaaaaa3aaaa', '約翰尼斯堡', CURRENT_TIMESTAMP);

---- 15. 購物車大項目資料 "cart"
INSERT INTO cart (cart_id, user_id, total_price) VALUES
('7bc2f92f-dafe-4cb2-9211-ffc67f16822e', 'a1b2c3d4-e5f6-7890-abcd-ef1234567890', 8721.69),
('83018530-f182-4734-afc2-cf4ecc96802d', 'a1b2c3d4-e5f6-7890-abcd-ef1234567890', 6263.64),
('65d6a65f-bcd8-4970-bf47-e28ae67a1c11', 'b2c3d4e5-f678-90ab-cdef-234567890abc', 3576.74),
('9221921d-33b0-4273-8e07-5fbb22acb772', 'b2c3d4e5-f678-90ab-cdef-234567890abc', 5769.06),
('7c09b1e1-8edc-44a7-a847-bdccf3153cfd', 'c3d4e5f6-7890-abcd-ef12-34567890abcd', 1610.73),
('08b4e271-f584-4297-9441-a299afb81098', 'c3d4e5f6-7890-abcd-ef12-34567890abcd', 6482.73);

---- 16. 購物車細項資料 "cart_item"
INSERT INTO cart_item (cart_item_id, cart_id, tour_id, quantity, start_date, end_date, room_type) VALUES
('c5cefe38-ff77-497c-b3fb-2831bbfb898c', '65d6a65f-bcd8-4970-bf47-e28ae67a1c11', '99999999-cccc-dddd-eeee-999999999999', 2, '2025-05-18', NULL, NULL),
('084a3d2b-f8d8-47f5-a977-47f225871375', '08b4e271-f584-4297-9441-a299afb81098', '22222222-bbbb-cccc-dddd-222222222222', 3, '2025-11-10', '2025-11-15', NULL),
('4936201b-d691-460b-97d0-000afae599c3', '7c09b1e1-8edc-44a7-a847-bdccf3153cfd', '11111111-aaaa-bbbb-cccc-111111111111', 1, '2025-12-01', '2025-12-05', NULL),
('f0e74ade-183f-4648-b9fe-cbb23458b89c', '9221921d-33b0-4273-8e07-5fbb22acb772', '88888888-bbbb-cccc-dddd-888888888888', 4, '2025-05-19', '2025-05-20', '豪華家庭房'),
('ecc926ca-d9f6-422f-8366-5d273236051b', '08b4e271-f584-4297-9441-a299afb81098', '44444444-dddd-eeee-ffff-444444444444', 3, '2025-05-15', '2025-05-16', NULL),
('f348640b-6ca0-4168-8615-6b19b4baf588', '65d6a65f-bcd8-4970-bf47-e28ae67a1c11', '66666666-ffff-aaaa-bbbb-666666666666', 5, '2025-10-15', '2025-10-22', NULL),
('70cc5744-2a87-4193-b503-1a5c73dc0b0c', '9221921d-33b0-4273-8e07-5fbb22acb772', '55555555-eeee-ffff-aaaa-555555555555', 2, '2025-05-14', '2025-05-15', '設計雙人房'),
('faa39aa2-6715-4dfa-bbac-2c6b1dc7de37', '65d6a65f-bcd8-4970-bf47-e28ae67a1c11', '00000000-dddd-eeee-ffff-000000000000', 3, '2025-11-05', '2025-11-15', NULL),
('c4b9e4b5-d0e9-4e5b-8884-7b115b6877de', '7c09b1e1-8edc-44a7-a847-bdccf3153cfd', '77777777-aaaa-bbbb-cccc-777777777777', 2, '2025-05-13', '2025-05-14', NULL),
('53f15e11-2350-4d9d-ade4-f4483af848da', '83018530-f182-4734-afc2-cf4ecc96802d', '33333333-cccc-dddd-eeee-333333333333', 3, '2025-05-16', NULL, NULL);

---- 17. 訂單大項目資料 "orders"
INSERT INTO orders (order_id, user_id, address, phone, payment_type, discount_type, payment_status, total_price, discount_price) VALUES
('c62e3ad6-19cc-4b58-bec7-231f41b678ac', 'b2c3d4e5-f678-90ab-cdef-234567890abc', '高雄市鼓山區美術館路45號', '0912345678', 'credit_card', 'none', 0, 3576.74, 794.83),
('58fcd7d9-62ee-4bbd-bfcd-086044ba4060', 'c3d4e5f6-7890-abcd-ef12-34567890abcd', '台中市西區公益路321巷9號', '0987654321', 'credit_card', 'none', 1, 6482.73, 439.63),
('f4977608-2efb-4725-94bc-b3265440b4c5', 'c3d4e5f6-7890-abcd-ef12-34567890abcd', '台北市中山區南京東路3段123號', '0978123456', 'atm', 'none', 0, 1610.73, 436.75),
('8c1e4f18-841e-49de-bc5e-c6754473f929', 'b2c3d4e5-f678-90ab-cdef-234567890abc', '台北市中山區南京東路3段123號', '0912345678', 'cvs', 'earlybird', 0, 5769.06, 839.86),
('8426dbe1-70cd-431c-b87a-5530a4d99a06', 'a1b2c3d4-e5f6-7890-abcd-ef1234567890', '台北市中山區南京東路3段123號', '0987654321', 'credit_card', 'none', 0, 6263.64, 596.12);


---- 18. 訂單細項資料 "order_item"
INSERT INTO order_item (order_item_id, order_id, tour_id, total_price, discount_price, payment_status, quantity, start_date, end_date, room_type) VALUES
('cac34fe5-c619-49dc-8cdd-79509e02f20b', 'c62e3ad6-19cc-4b58-bec7-231f41b678ac', '99999999-cccc-dddd-eeee-999999999999', 4500, 3800, 1, 2, '2025-05-18', NULL, NULL),
('f3d2d83e-f782-41dc-8e52-0b49a2cfce0d', '58fcd7d9-62ee-4bbd-bfcd-086044ba4060', '22222222-bbbb-cccc-dddd-222222222222', 5500, 2000, 2, 3, '2025-11-10', '2025-11-15', NULL),
('d19eaf9b-cef7-4053-b807-e54532b86dd0', 'f4977608-2efb-4725-94bc-b3265440b4c5', '11111111-aaaa-bbbb-cccc-111111111111', 1200, 800, 3, 1, '2025-12-01', '2025-12-05', NULL),
('31ff7da9-f987-426b-b0bd-f5a03c5d9d9a', '8c1e4f18-841e-49de-bc5e-c6754473f929', '88888888-bbbb-cccc-dddd-888888888888', 7000, NULL, 1, 4, '2025-05-19', '2025-05-20', '豪華家庭房'),
('5739fb80-cd14-43ac-91c8-da6c132238b5', '58fcd7d9-62ee-4bbd-bfcd-086044ba4060', '44444444-dddd-eeee-ffff-444444444444', 8400, NULL, 1, 3, '2025-05-15', '2025-05-16', NULL),
('36a2abc9-dd5f-4ff4-8f1f-29f70067655e', 'c62e3ad6-19cc-4b58-bec7-231f41b678ac', '66666666-ffff-aaaa-bbbb-666666666666', 4900, 4000, 3, 5, '2025-10-15', '2025-10-22', NULL),
('363eaf2c-772f-4b71-bc1c-132454d3c212', '8c1e4f18-841e-49de-bc5e-c6754473f929', '55555555-eeee-ffff-aaaa-555555555555', 8800, NULL, 1, 2, '2025-05-14', '2025-05-15', '設計雙人房'),
('0adab552-7e49-412d-9ca7-dbd7cf455f7f', 'c62e3ad6-19cc-4b58-bec7-231f41b678ac', '00000000-dddd-eeee-ffff-000000000000', 4800, 3500, 1, 3, '2025-11-05', '2025-11-15', NULL),
('e6b85926-697a-4a79-9d6a-b87de5f5819e', 'f4977608-2efb-4725-94bc-b3265440b4c5', '77777777-aaaa-bbbb-cccc-777777777777', 7700, 7000, 1, 2, '2025-05-13', '2025-05-14', NULL),
('5c8096e9-9771-4b1a-982c-d6c5fed5521c', '8426dbe1-70cd-431c-b87a-5530a4d99a06', '33333333-cccc-dddd-eeee-333333333333', 6900, NULL, 3, 3, '2025-05-16', NULL, NULL);

---- 19. 付款紀錄資料 "payment"

---- 20. 評論資料 "review"
INSERT INTO "review" (
    review_id, user_id, tour_id, type, hashtag, rating, content, created_at, updated_at
) VALUES
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567890', NULL, 'web', '#操作直覺', 5, '整個網站設計非常友善，喜歡！', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'b2c3d4e5-f678-90ab-cdef-234567890abc', NULL, 'web', '#速度很快', 4, '下單流程簡單又快速，推薦。', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'c3d4e5f6-7890-abcd-ef12-34567890abcd', '00000000-dddd-eeee-ffff-000000000000', 'travel', NULL, 5, '北海道行程安排完美，超值！', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567890', '11111111-aaaa-bbbb-cccc-111111111111', 'travel', NULL, 4, '巴黎巡禮浪漫又美麗！', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'b2c3d4e5-f678-90ab-cdef-234567890abc', '22222222-bbbb-cccc-dddd-222222222222', 'hotel', NULL, 5, '飯店地點方便，乾淨舒適。', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'c3d4e5f6-7890-abcd-ef12-34567890abcd', '33333333-cccc-dddd-eeee-333333333333', 'hotel', NULL, 4, '設施不錯但早餐普通。', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567890', '44444444-dddd-eeee-ffff-444444444444', 'food', NULL, 5, '曼谷美食超級好吃，值得一試！', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'b2c3d4e5-f678-90ab-cdef-234567890abc', '55555555-eeee-ffff-aaaa-555555555555', 'food', NULL, 3, '有些小吃偏油但整體好吃。', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'c3d4e5f6-7890-abcd-ef12-34567890abcd', '66666666-ffff-aaaa-bbbb-666666666666', 'spot', NULL, 5, '景色壯觀，很值得一遊！', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567890', '77777777-aaaa-bbbb-cccc-777777777777', 'spot', NULL, 4, '景點人潮多但風景超美。', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

---- 21. 隱藏玩法資料 "hidden_play"
INSERT INTO "hidden_play" (
    hidden_play_id, user_id, tour_id, title, content, share_url, created_at, updated_at
) VALUES
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567890', '00000000-dddd-eeee-ffff-000000000000', '北海道隱藏雪景', '小巷裡的冰雕展超夢幻，遊客很少！', 'https://example.com/hidden/hokkaido-snow', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'b2c3d4e5-f678-90ab-cdef-234567890abc', '11111111-aaaa-bbbb-cccc-111111111111', '巴黎秘境咖啡廳', '塞納河旁的小咖啡廳，超有文青感。', 'https://example.com/hidden/paris-cafe', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'c3d4e5f6-7890-abcd-ef12-34567890abcd', '22222222-bbbb-cccc-dddd-222222222222', '隱藏版清邁夜市', '本地人推薦的夜市小吃，便宜又好吃。', 'https://example.com/hidden/chiangmai-market', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567890', '33333333-cccc-dddd-eeee-333333333333', '秘密海灘', '搭乘小船才能到達的超夢幻海灘。', 'https://example.com/hidden/secret-beach', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'b2c3d4e5-f678-90ab-cdef-234567890abc', '44444444-dddd-eeee-ffff-444444444444', '曼谷隱藏美食街', '巷弄內隱藏的米其林推薦小吃。', 'https://example.com/hidden/bangkok-food', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'c3d4e5f6-7890-abcd-ef12-34567890abcd', '55555555-eeee-ffff-aaaa-555555555555', '紐約市秘密書店', '藏身公園旁的獨立書店，超有味道。', 'https://example.com/hidden/nyc-bookstore', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

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
);

---- 23. 使用者收藏旅遊商品 "favorite"
INSERT INTO "favorite" (
    favorite_id, user_id, tour_id, created_at, updated_at
) VALUES
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567890', '00000000-dddd-eeee-ffff-000000000000', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'b2c3d4e5-f678-90ab-cdef-234567890abc', '11111111-aaaa-bbbb-cccc-111111111111', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'c3d4e5f6-7890-abcd-ef12-34567890abcd', '22222222-bbbb-cccc-dddd-222222222222', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567890', '22222222-bbbb-cccc-dddd-222222222222', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567890', '33333333-cccc-dddd-eeee-333333333333', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'b2c3d4e5-f678-90ab-cdef-234567890abc', '44444444-dddd-eeee-ffff-444444444444', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'c3d4e5f6-7890-abcd-ef12-34567890abcd', '55555555-eeee-ffff-aaaa-555555555555', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);


---- 24. 會員旅遊積分資料 "point_record"
INSERT INTO point_record (point_id, user_id, order_id, type, point) VALUES
('a2e85047-514d-486e-ba0e-b41adf788ea3', 'c3d4e5f6-7890-abcd-ef12-34567890abcd', 'f4977608-2efb-4725-94bc-b3265440b4c5', '新增', 1610),
('3c9e2b67-1478-4669-adeb-a5bef809d537', 'c3d4e5f6-7890-abcd-ef12-34567890abcd', 'f4977608-2efb-4725-94bc-b3265440b4c5', '減少', -436);


---- 25. 優惠卷與使用者綁定的資料 "user_coupon"
INSERT INTO "user_coupon" (
    user_coupon_id, user_id, order_id, coupon_id, status
) VALUES
('6f610e1c-51cf-4709-b8e2-5b8b96751100', 'b2c3d4e5-f678-90ab-cdef-234567890abc', 'c62e3ad6-19cc-4b58-bec7-231f41b678ac', '33333333-cccc-dddd-eeee-333333333333', 1),
('079a19f1-679d-4282-b047-e57d40b473f8', 'c3d4e5f6-7890-abcd-ef12-34567890abcd', NULL, '33333333-cccc-dddd-eeee-333333333333', 0),
('870df12e-1ec6-49da-8f91-3ffefb4ca8b0', 'b2c3d4e5-f678-90ab-cdef-234567890abc', '8c1e4f18-841e-49de-bc5e-c6754473f929', '44444444-dddd-eeee-ffff-444444444444', 1),
('4b202c03-9bde-4c8c-9c03-f23aac550c03', 'a1b2c3d4-e5f6-7890-abcd-ef1234567890', '8426dbe1-70cd-431c-b87a-5530a4d99a06', '44444444-dddd-eeee-ffff-444444444444', 1);
