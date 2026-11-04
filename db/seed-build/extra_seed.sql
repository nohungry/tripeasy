-- P1b Task 3：補到契約 §0.1「seed 目標值（定案）」的資料。格式同 fakedata，由 build_seed.py 併進來源檔。
-- 主鍵是可讀的佔位字面值（extra-*）或 uuid_generate_v4()，build_seed.py 會依自然鍵換成 v4 形狀的 id；
-- 外鍵可以指到來源檔的舊 id，一起換掉。日期以 2025-05-20 為基準，由 shift_dates 平移到載入日。
-- orders / order_item / point_record 取代來源檔的列（build_seed.py 會先丟掉來源檔那些列）。
-- payment.return_data 留 NULL：內含新的 order_id，由 build_seed.py 在 id 換完後填入。

---- 5. 旅遊項目資料 "tour"（新增 13 個）
INSERT INTO "tour" (tour_id, type, item, status, title, slogan, tour_start_date, tour_end_date, days, price, country, region, address, google_map_url, calendar_url, preference1, preference2, preference3, notice, description, cover_image, img1, img1_desc, img2, img2_desc, img3, img3_desc, img4, img4_desc, img5, img5_desc, img6, img6_desc, created_at, updated_at) VALUES
('extra-tour-01', 'tourgroup', 'travel', 1, '冰島極光 8 日探索', '追逐綠色光幕的極地冒險', '2025-12-26 00:00:00', '2026-01-02 23:59:59', 8, 120000, 'Iceland', 'Reykjavik', '雷克雅維克港區', 'https://goo.gl/maps/extra1', 'https://calendar.google.com/event?extra1', 4, 5, 1, '請攜帶保暖衣物與防滑鞋。', '環島追極光、藍湖溫泉與冰河健行。', 'https://example.com/images/cover11.jpg', 'https://example.com/images/11-1.jpg', 'Reykjavik景點1', 'https://example.com/images/11-2.jpg', 'Reykjavik景點2', 'https://example.com/images/11-3.jpg', 'Reykjavik景點3', 'https://example.com/images/11-4.jpg', 'Reykjavik景點4', 'https://example.com/images/11-5.jpg', 'Reykjavik景點5', 'https://example.com/images/11-6.jpg', 'Reykjavik景點6', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('extra-tour-02', 'tourgroup', 'travel', 1, '瑞士鐵道山岳 7 日', '搭乘景觀列車穿越阿爾卑斯', '2025-08-28 00:00:00', '2025-09-03 23:59:59', 7, 110000, 'Switzerland', 'Zurich', '蘇黎世中央車站', 'https://goo.gl/maps/extra2', 'https://calendar.google.com/event?extra2', 2, 6, 4, '高山行程請注意高度適應。', '冰河列車、少女峰與策馬特小鎮。', 'https://example.com/images/cover12.jpg', 'https://example.com/images/12-1.jpg', 'Zurich景點1', 'https://example.com/images/12-2.jpg', 'Zurich景點2', 'https://example.com/images/12-3.jpg', 'Zurich景點3', 'https://example.com/images/12-4.jpg', 'Zurich景點4', 'https://example.com/images/12-5.jpg', 'Zurich景點5', 'https://example.com/images/12-6.jpg', 'Zurich景點6', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('extra-tour-03', 'tourgroup', 'travel', 1, '西班牙陽光巡禮 9 日', '熱情陽光下的建築與美食', '2025-07-19 00:00:00', '2025-07-27 23:59:59', 9, 90000, 'Spain', 'Madrid', '馬德里太陽門廣場', 'https://goo.gl/maps/extra3', 'https://calendar.google.com/event?extra3', 3, 1, 7, '夏季氣溫高，請做好防曬。', '高第建築、佛朗明哥與海鮮燉飯。', 'https://example.com/images/cover13.jpg', 'https://example.com/images/13-1.jpg', 'Madrid景點1', 'https://example.com/images/13-2.jpg', 'Madrid景點2', 'https://example.com/images/13-3.jpg', 'Madrid景點3', 'https://example.com/images/13-4.jpg', 'Madrid景點4', 'https://example.com/images/13-5.jpg', 'Madrid景點5', 'https://example.com/images/13-6.jpg', 'Madrid景點6', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('extra-tour-04', 'backpacker', 'food', 1, '台南小吃巡禮', '一口一口吃遍府城', NULL, NULL, 0, 3000, 'Taiwan', 'Tainan', '台南中西區國華街', 'https://goo.gl/maps/extra4', 'https://calendar.google.com/event?extra4', 1, 3, 2, '部分店家週一公休。', '從牛肉湯到碗粿，走訪在地老店。', 'https://example.com/images/cover14.jpg', 'https://example.com/images/14-1.jpg', 'Tainan景點1', 'https://example.com/images/14-2.jpg', 'Tainan景點2', 'https://example.com/images/14-3.jpg', 'Tainan景點3', 'https://example.com/images/14-4.jpg', 'Tainan景點4', 'https://example.com/images/14-5.jpg', 'Tainan景點5', 'https://example.com/images/14-6.jpg', 'Tainan景點6', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('extra-tour-05', 'backpacker', 'food', 1, '東京拉麵地圖', '一碗一碗找出本命拉麵', NULL, NULL, 0, 4500, 'Japan', 'Tokyo', '東京新宿區', 'https://goo.gl/maps/extra5', 'https://calendar.google.com/event?extra5', 3, 2, 1, '熱門店家需排隊。', '豚骨、醬油、沾麵的人氣名店路線。', 'https://example.com/images/cover15.jpg', 'https://example.com/images/15-1.jpg', 'Tokyo景點1', 'https://example.com/images/15-2.jpg', 'Tokyo景點2', 'https://example.com/images/15-3.jpg', 'Tokyo景點3', 'https://example.com/images/15-4.jpg', 'Tokyo景點4', 'https://example.com/images/15-5.jpg', 'Tokyo景點5', 'https://example.com/images/15-6.jpg', 'Tokyo景點6', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('extra-tour-06', 'backpacker', 'food', 1, '曼谷街頭美食', '夜市與路邊攤的泰式滋味', NULL, NULL, 0, 3800, 'Thailand', 'Bangkok', '曼谷耀華力路', 'https://goo.gl/maps/extra6', 'https://calendar.google.com/event?extra6', 2, 3, 1, '請注意食物辣度。', '船麵、芒果糯米飯與炭烤海鮮。', 'https://example.com/images/cover16.jpg', 'https://example.com/images/16-1.jpg', 'Bangkok景點1', 'https://example.com/images/16-2.jpg', 'Bangkok景點2', 'https://example.com/images/16-3.jpg', 'Bangkok景點3', 'https://example.com/images/16-4.jpg', 'Bangkok景點4', 'https://example.com/images/16-5.jpg', 'Bangkok景點5', 'https://example.com/images/16-6.jpg', 'Bangkok景點6', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('extra-tour-07', 'backpacker', 'spot', 1, '京都古寺散步', '在千年古都慢慢走', NULL, NULL, 0, 6000, 'Japan', 'Kyoto', '京都東山區', 'https://goo.gl/maps/extra7', 'https://calendar.google.com/event?extra7', 5, 2, 3, '寺院內請保持安靜。', '清水寺、伏見稻荷與嵐山竹林。', 'https://example.com/images/cover17.jpg', 'https://example.com/images/17-1.jpg', 'Kyoto景點1', 'https://example.com/images/17-2.jpg', 'Kyoto景點2', 'https://example.com/images/17-3.jpg', 'Kyoto景點3', 'https://example.com/images/17-4.jpg', 'Kyoto景點4', 'https://example.com/images/17-5.jpg', 'Kyoto景點5', 'https://example.com/images/17-6.jpg', 'Kyoto景點6', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('extra-tour-08', 'backpacker', 'spot', 1, '倫敦博物館漫遊', '免費博物館裡的大英收藏', NULL, NULL, 0, 7500, 'UK', 'London', '倫敦布盧姆斯伯里', 'https://goo.gl/maps/extra8', 'https://calendar.google.com/event?extra8', 4, 5, 2, '部分展館需預約時段。', '大英博物館、自然史博物館與泰特現代館。', 'https://example.com/images/cover18.jpg', 'https://example.com/images/18-1.jpg', 'London景點1', 'https://example.com/images/18-2.jpg', 'London景點2', 'https://example.com/images/18-3.jpg', 'London景點3', 'https://example.com/images/18-4.jpg', 'London景點4', 'https://example.com/images/18-5.jpg', 'London景點5', 'https://example.com/images/18-6.jpg', 'London景點6', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('extra-tour-09', 'backpacker', 'spot', 1, '新加坡花園城市導覽', '鋼骨叢林裡的綠色奇蹟', NULL, NULL, 0, 6800, 'Singapore', 'Singapore', '新加坡濱海灣', 'https://goo.gl/maps/extra9', 'https://calendar.google.com/event?extra9', 6, 4, 2, '戶外行程請準備雨具。', '濱海灣花園、植物園與小印度街區。', 'https://example.com/images/cover19.jpg', 'https://example.com/images/19-1.jpg', 'Singapore景點1', 'https://example.com/images/19-2.jpg', 'Singapore景點2', 'https://example.com/images/19-3.jpg', 'Singapore景點3', 'https://example.com/images/19-4.jpg', 'Singapore景點4', 'https://example.com/images/19-5.jpg', 'Singapore景點5', 'https://example.com/images/19-6.jpg', 'Singapore景點6', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('extra-tour-10', 'backpacker', 'hotel', 1, '沖繩海景度假旅店', '推開窗就是蔚藍海岸', NULL, NULL, 0, 8800, 'Japan', 'Okinawa', '那霸市美榮橋', 'https://goo.gl/maps/extra10', 'https://calendar.google.com/event?extra10', 1, 4, 2, '入住時間下午三點起。', '全海景客房，步行即可到海灘。', 'https://example.com/images/cover20.jpg', 'https://example.com/images/20-1.jpg', 'Okinawa景點1', 'https://example.com/images/20-2.jpg', 'Okinawa景點2', 'https://example.com/images/20-3.jpg', 'Okinawa景點3', 'https://example.com/images/20-4.jpg', 'Okinawa景點4', 'https://example.com/images/20-5.jpg', 'Okinawa景點5', 'https://example.com/images/20-6.jpg', 'Okinawa景點6', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('extra-tour-11', 'backpacker', 'hotel', 1, '峇里島別墅旅宿', '私人泳池的熱帶度假', NULL, NULL, 0, 12000, 'Indonesia', 'Bali', '烏布稻田區', 'https://goo.gl/maps/extra11', 'https://calendar.google.com/event?extra11', 2, 4, 6, '別墅內禁止明火。', '獨棟別墅附泳池，含每日早餐。', 'https://example.com/images/cover21.jpg', 'https://example.com/images/21-1.jpg', 'Bali景點1', 'https://example.com/images/21-2.jpg', 'Bali景點2', 'https://example.com/images/21-3.jpg', 'Bali景點3', 'https://example.com/images/21-4.jpg', 'Bali景點4', 'https://example.com/images/21-5.jpg', 'Bali景點5', 'https://example.com/images/21-6.jpg', 'Bali景點6', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('extra-tour-12', 'backpacker', 'hotel', 1, '河內古城精品旅店', '住進老城區的法式小樓', NULL, NULL, 0, 6500, 'Vietnam', 'Hanoi', '河內還劍區', 'https://goo.gl/maps/extra12', 'https://calendar.google.com/event?extra12', 3, 5, 1, '老城區夜間較為吵雜。', '步行可達水上木偶劇院與夜市。', 'https://example.com/images/cover22.jpg', 'https://example.com/images/22-1.jpg', 'Hanoi景點1', 'https://example.com/images/22-2.jpg', 'Hanoi景點2', 'https://example.com/images/22-3.jpg', 'Hanoi景點3', 'https://example.com/images/22-4.jpg', 'Hanoi景點4', 'https://example.com/images/22-5.jpg', 'Hanoi景點5', 'https://example.com/images/22-6.jpg', 'Hanoi景點6', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('extra-tour-13', 'backpacker', 'hotel', 1, '釜山海岸旅店', '聽著海浪入睡的港都旅宿', NULL, NULL, 0, 7200, 'Korea', 'Busan', '釜山海雲台', 'https://goo.gl/maps/extra13', 'https://calendar.google.com/event?extra13', 1, 2, 5, '海景房數量有限。', '海雲台海灘旁，附設早餐咖啡廳。', 'https://example.com/images/cover23.jpg', 'https://example.com/images/23-1.jpg', 'Busan景點1', 'https://example.com/images/23-2.jpg', 'Busan景點2', 'https://example.com/images/23-3.jpg', 'Busan景點3', 'https://example.com/images/23-4.jpg', 'Busan景點4', 'https://example.com/images/23-5.jpg', 'Busan景點5', 'https://example.com/images/23-6.jpg', 'Busan景點6', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

---- 6. 旅遊產品細項資料 "tour_detail"
INSERT INTO "tour_detail" (tour_detail_id, tour_id, feature_img1, feature_desc1, feature_img2, feature_desc2, feature_img3, feature_desc3, itinerary, created_at, updated_at) VALUES
('extra-td-01', 'extra-tour-01', 'https://example.com/feature/extra1-1.jpg', 'Reykjavik特色一', 'https://example.com/feature/extra1-2.jpg', 'Reykjavik特色二', 'https://example.com/feature/extra1-3.jpg', 'Reykjavik特色三', 'Day1: Reykjavik行程1,Day2: Reykjavik行程2,Day3: Reykjavik行程3,Day4: Reykjavik行程4,Day5: Reykjavik行程5,Day6: Reykjavik行程6,Day7: Reykjavik行程7,Day8: Reykjavik行程8', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('extra-td-02', 'extra-tour-02', 'https://example.com/feature/extra2-1.jpg', 'Zurich特色一', 'https://example.com/feature/extra2-2.jpg', 'Zurich特色二', 'https://example.com/feature/extra2-3.jpg', 'Zurich特色三', 'Day1: Zurich行程1,Day2: Zurich行程2,Day3: Zurich行程3,Day4: Zurich行程4,Day5: Zurich行程5,Day6: Zurich行程6,Day7: Zurich行程7', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('extra-td-03', 'extra-tour-03', 'https://example.com/feature/extra3-1.jpg', 'Madrid特色一', 'https://example.com/feature/extra3-2.jpg', 'Madrid特色二', 'https://example.com/feature/extra3-3.jpg', 'Madrid特色三', 'Day1: Madrid行程1,Day2: Madrid行程2,Day3: Madrid行程3,Day4: Madrid行程4,Day5: Madrid行程5,Day6: Madrid行程6,Day7: Madrid行程7,Day8: Madrid行程8,Day9: Madrid行程9', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('extra-td-04', 'extra-tour-04', 'https://example.com/feature/extra4-1.jpg', 'Tainan特色一', 'https://example.com/feature/extra4-2.jpg', 'Tainan特色二', 'https://example.com/feature/extra4-3.jpg', 'Tainan特色三', 'Day1: Tainan行程1,Day2: Tainan行程2,Day3: Tainan行程3', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('extra-td-05', 'extra-tour-05', 'https://example.com/feature/extra5-1.jpg', 'Tokyo特色一', 'https://example.com/feature/extra5-2.jpg', 'Tokyo特色二', 'https://example.com/feature/extra5-3.jpg', 'Tokyo特色三', 'Day1: Tokyo行程1,Day2: Tokyo行程2,Day3: Tokyo行程3', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('extra-td-06', 'extra-tour-06', 'https://example.com/feature/extra6-1.jpg', 'Bangkok特色一', 'https://example.com/feature/extra6-2.jpg', 'Bangkok特色二', 'https://example.com/feature/extra6-3.jpg', 'Bangkok特色三', 'Day1: Bangkok行程1,Day2: Bangkok行程2,Day3: Bangkok行程3', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('extra-td-07', 'extra-tour-07', 'https://example.com/feature/extra7-1.jpg', 'Kyoto特色一', 'https://example.com/feature/extra7-2.jpg', 'Kyoto特色二', 'https://example.com/feature/extra7-3.jpg', 'Kyoto特色三', 'Day1: Kyoto行程1,Day2: Kyoto行程2,Day3: Kyoto行程3', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('extra-td-08', 'extra-tour-08', 'https://example.com/feature/extra8-1.jpg', 'London特色一', 'https://example.com/feature/extra8-2.jpg', 'London特色二', 'https://example.com/feature/extra8-3.jpg', 'London特色三', 'Day1: London行程1,Day2: London行程2,Day3: London行程3', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('extra-td-09', 'extra-tour-09', 'https://example.com/feature/extra9-1.jpg', 'Singapore特色一', 'https://example.com/feature/extra9-2.jpg', 'Singapore特色二', 'https://example.com/feature/extra9-3.jpg', 'Singapore特色三', 'Day1: Singapore行程1,Day2: Singapore行程2,Day3: Singapore行程3', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('extra-td-10', 'extra-tour-10', 'https://example.com/feature/extra10-1.jpg', 'Okinawa特色一', 'https://example.com/feature/extra10-2.jpg', 'Okinawa特色二', 'https://example.com/feature/extra10-3.jpg', 'Okinawa特色三', 'Day1: Okinawa行程1,Day2: Okinawa行程2,Day3: Okinawa行程3', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('extra-td-11', 'extra-tour-11', 'https://example.com/feature/extra11-1.jpg', 'Bali特色一', 'https://example.com/feature/extra11-2.jpg', 'Bali特色二', 'https://example.com/feature/extra11-3.jpg', 'Bali特色三', 'Day1: Bali行程1,Day2: Bali行程2,Day3: Bali行程3', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('extra-td-12', 'extra-tour-12', 'https://example.com/feature/extra12-1.jpg', 'Hanoi特色一', 'https://example.com/feature/extra12-2.jpg', 'Hanoi特色二', 'https://example.com/feature/extra12-3.jpg', 'Hanoi特色三', 'Day1: Hanoi行程1,Day2: Hanoi行程2,Day3: Hanoi行程3', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('extra-td-13', 'extra-tour-13', 'https://example.com/feature/extra13-1.jpg', 'Busan特色一', 'https://example.com/feature/extra13-2.jpg', 'Busan特色二', 'https://example.com/feature/extra13-3.jpg', 'Busan特色三', 'Day1: Busan行程1,Day2: Busan行程2,Day3: Busan行程3', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

---- 7. 美食專區資料 "restaurant"
INSERT INTO "restaurant" (restaurant_id, tour_id, reservation_limit, website_info, website_url, created_at, updated_at) VALUES
('extra-restaurant-01', 'extra-tour-04', 40, 'Tainan在地人氣店家集合，預約即享專屬美食地圖。', 'https://example.com/extra-food-tour-1', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('extra-restaurant-02', 'extra-tour-05', 40, 'Tokyo在地人氣店家集合，預約即享專屬美食地圖。', 'https://example.com/extra-food-tour-2', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('extra-restaurant-03', 'extra-tour-06', 40, 'Bangkok在地人氣店家集合，預約即享專屬美食地圖。', 'https://example.com/extra-food-tour-3', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

---- 8. 美食專區營業資料 "restaurant_business"
INSERT INTO "restaurant_business" (restaurant_business_id, restaurant_id, week, business_hours, created_at, updated_at) VALUES
('extra-business-01-1', 'extra-restaurant-01', 'Monday', '11:00~14:00, 17:00~21:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('extra-business-01-2', 'extra-restaurant-01', 'Tuesday', '11:00~14:00, 17:00~21:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('extra-business-01-3', 'extra-restaurant-01', 'Wednesday', '11:00~14:00, 17:00~21:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('extra-business-01-4', 'extra-restaurant-01', 'Thursday', '11:00~14:00, 17:00~21:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('extra-business-01-5', 'extra-restaurant-01', 'Friday', '11:00~14:00, 17:00~21:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('extra-business-01-6', 'extra-restaurant-01', 'Saturday', '11:00~14:00, 17:00~21:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('extra-business-01-7', 'extra-restaurant-01', 'Sunday', '11:00~14:00, 17:00~21:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('extra-business-02-1', 'extra-restaurant-02', 'Monday', '11:00~14:00, 17:00~21:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('extra-business-02-2', 'extra-restaurant-02', 'Tuesday', '11:00~14:00, 17:00~21:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('extra-business-02-3', 'extra-restaurant-02', 'Wednesday', '11:00~14:00, 17:00~21:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('extra-business-02-4', 'extra-restaurant-02', 'Thursday', '11:00~14:00, 17:00~21:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('extra-business-02-5', 'extra-restaurant-02', 'Friday', '11:00~14:00, 17:00~21:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('extra-business-02-6', 'extra-restaurant-02', 'Saturday', '11:00~14:00, 17:00~21:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('extra-business-02-7', 'extra-restaurant-02', 'Sunday', '11:00~14:00, 17:00~21:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('extra-business-03-1', 'extra-restaurant-03', 'Monday', '11:00~14:00, 17:00~21:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('extra-business-03-2', 'extra-restaurant-03', 'Tuesday', '11:00~14:00, 17:00~21:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('extra-business-03-3', 'extra-restaurant-03', 'Wednesday', '11:00~14:00, 17:00~21:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('extra-business-03-4', 'extra-restaurant-03', 'Thursday', '11:00~14:00, 17:00~21:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('extra-business-03-5', 'extra-restaurant-03', 'Friday', '11:00~14:00, 17:00~21:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('extra-business-03-6', 'extra-restaurant-03', 'Saturday', '11:00~14:00, 17:00~21:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('extra-business-03-7', 'extra-restaurant-03', 'Sunday', '11:00~14:00, 17:00~21:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

---- 9. 美食專區菜單資料 "restaurant_menu"
INSERT INTO "restaurant_menu" (restaurant_menu_id, restaurant_id, name, price, description, created_at, updated_at) VALUES
('extra-menu-01-1', 'extra-restaurant-01', 'Tainan招牌小吃', 120.0, 'Tainan在地人推薦。', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('extra-menu-01-2', 'extra-restaurant-01', 'Tainan特調飲品', 80.0, 'Tainan在地人推薦。', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('extra-menu-02-1', 'extra-restaurant-02', 'Tokyo招牌小吃', 120.0, 'Tokyo在地人推薦。', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('extra-menu-02-2', 'extra-restaurant-02', 'Tokyo特調飲品', 80.0, 'Tokyo在地人推薦。', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('extra-menu-03-1', 'extra-restaurant-03', 'Bangkok招牌小吃', 120.0, 'Bangkok在地人推薦。', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('extra-menu-03-2', 'extra-restaurant-03', 'Bangkok特調飲品', 80.0, 'Bangkok在地人推薦。', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

---- 10. 飯店專區資料 "hotel"
INSERT INTO "hotel" (hotel_id, tour_id, facility_desc, food_desc, room_desc, leisure_desc, traffic_desc, other_desc, created_at, updated_at) VALUES
('extra-hotel-01', 'extra-tour-10', '24 小時櫃台服務, 免費 Wi-Fi, 行李寄存服務', '早餐供應', '冷氣/暖氣, 獨立衛浴', '游泳池（室外）', '接駁巴士（市區）', '叫車/叫計程車', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('extra-hotel-02', 'extra-tour-11', '24 小時櫃台服務, 免費 Wi-Fi, 行李寄存服務', '早餐供應', '冷氣/暖氣, 獨立衛浴', '游泳池（室外）', '接駁巴士（市區）', '叫車/叫計程車', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('extra-hotel-03', 'extra-tour-12', '24 小時櫃台服務, 免費 Wi-Fi, 行李寄存服務', '早餐供應', '冷氣/暖氣, 獨立衛浴', '游泳池（室外）', '接駁巴士（市區）', '叫車/叫計程車', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('extra-hotel-04', 'extra-tour-13', '24 小時櫃台服務, 免費 Wi-Fi, 行李寄存服務', '早餐供應', '冷氣/暖氣, 獨立衛浴', '游泳池（室外）', '接駁巴士（市區）', '叫車/叫計程車', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

---- 11. 飯店專區客房資料 "hotel_room"
INSERT INTO "hotel_room" (hotel_room_id, hotel_id, title, capacity, room_count, image, image_desc, created_at, updated_at) VALUES
('extra-room-01-1', 'extra-hotel-01', '海景雙人房', 2, 6, 'https://example.com/images/hotel_extra1_room1.jpg', 'Okinawa客房', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('extra-room-01-2', 'extra-hotel-01', '海景家庭房', 4, 6, 'https://example.com/images/hotel_extra1_room2.jpg', 'Okinawa客房', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('extra-room-02-1', 'extra-hotel-02', 'Bali雙人房', 2, 6, 'https://example.com/images/hotel_extra2_room1.jpg', 'Bali客房', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('extra-room-02-2', 'extra-hotel-02', 'Bali家庭房', 4, 6, 'https://example.com/images/hotel_extra2_room2.jpg', 'Bali客房', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('extra-room-03-1', 'extra-hotel-03', 'Hanoi雙人房', 2, 6, 'https://example.com/images/hotel_extra3_room1.jpg', 'Hanoi客房', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('extra-room-03-2', 'extra-hotel-03', 'Hanoi家庭房', 4, 6, 'https://example.com/images/hotel_extra3_room2.jpg', 'Hanoi客房', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('extra-room-04-1', 'extra-hotel-04', 'Busan雙人房', 2, 6, 'https://example.com/images/hotel_extra4_room1.jpg', 'Busan客房', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('extra-room-04-2', 'extra-hotel-04', 'Busan家庭房', 4, 6, 'https://example.com/images/hotel_extra4_room2.jpg', 'Busan客房', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

---- 12. 重要通知資料(促銷/異動) "notification"（新增促銷）
INSERT INTO "notification" (notification_id, tour_id, type, start_date, end_date, discount, promo_price, change_desc, created_at, updated_at) VALUES
(uuid_generate_v4(), 'extra-tour-01', '促銷', '2025-05-13 00:00:00', '2025-06-03 23:59:59', 10.0, 108000.0, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'extra-tour-02', '促銷', '2025-05-17 00:00:00', '2025-06-19 23:59:59', 20.0, 88000.0, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'extra-tour-03', '促銷', '2025-05-19 00:00:00', '2025-05-27 23:59:59', 10.0, 81000.0, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'extra-tour-04', '促銷', '2025-05-30 00:00:00', '2025-06-29 23:59:59', 10.0, 2700.0, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'extra-tour-07', '促銷', '2025-04-10 00:00:00', '2025-05-10 23:59:59', 10.0, 5400.0, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

---- 17. 訂單大項目資料 "orders"（取代來源檔的 5 列）
INSERT INTO orders (order_id, user_id, address, phone, payment_type, discount_type, payment_status, total_price, discount_price, created_at, updated_at) VALUES
('extra-order-01', 'a1b2c3d4-e5f6-7890-abcd-ef1234567890', '台北市中山區南京東路3段123號', '0987654321', 'credit_card', 'none', 1, 45000, NULL, CURRENT_TIMESTAMP - INTERVAL '9 days', CURRENT_TIMESTAMP - INTERVAL '9 days'),
('extra-order-02', 'b2c3d4e5-f678-90ab-cdef-234567890abc', '高雄市鼓山區美術館路45號', '0912345678', 'credit_card', 'coupon', 1, 45000, 44990, CURRENT_TIMESTAMP - INTERVAL '8 days', CURRENT_TIMESTAMP - INTERVAL '8 days'),
('extra-order-03', 'c3d4e5f6-7890-abcd-ef12-34567890abcd', '台中市西區公益路321巷9號', '0987654321', 'credit_card', 'none', 1, 45000, NULL, CURRENT_TIMESTAMP - INTERVAL '7 days', CURRENT_TIMESTAMP - INTERVAL '7 days'),
('extra-order-04', 'a1b2c3d4-e5f6-7890-abcd-ef1234567890', '台北市中山區南京東路3段123號', '0987654321', 'credit_card', 'coupon', 1, 98000, 97700, CURRENT_TIMESTAMP - INTERVAL '4 days', CURRENT_TIMESTAMP - INTERVAL '4 days'),
('extra-order-05', 'c3d4e5f6-7890-abcd-ef12-34567890abcd', '台中市西區公益路321巷9號', '0987654321', 'atm', 'none', 1, 98000, NULL, CURRENT_TIMESTAMP - INTERVAL '3 days', CURRENT_TIMESTAMP - INTERVAL '3 days'),
('extra-order-06', 'b2c3d4e5-f678-90ab-cdef-234567890abc', '高雄市鼓山區美術館路45號', '0912345678', 'credit_card', 'coupon', 1, 85000, 84700, CURRENT_TIMESTAMP - INTERVAL '30 days', CURRENT_TIMESTAMP - INTERVAL '30 days'),
('extra-order-07', 'a1b2c3d4-e5f6-7890-abcd-ef1234567890', '台北市中山區南京東路3段123號', '0987654321', 'credit_card', 'point', 1, 8400, 8200, CURRENT_TIMESTAMP - INTERVAL '29 days', CURRENT_TIMESTAMP - INTERVAL '29 days'),
('extra-order-08', 'b2c3d4e5-f678-90ab-cdef-234567890abc', '高雄市鼓山區美術館路45號', '0912345678', 'cvs', 'none', 1, 12600, NULL, CURRENT_TIMESTAMP - INTERVAL '28 days', CURRENT_TIMESTAMP - INTERVAL '28 days'),
('extra-order-09', 'c3d4e5f6-7890-abcd-ef12-34567890abcd', '台中市西區公益路321巷9號', '0987654321', 'credit_card', 'point', 1, 30000, 29680, CURRENT_TIMESTAMP - INTERVAL '27 days', CURRENT_TIMESTAMP - INTERVAL '27 days'),
('extra-order-10', 'a1b2c3d4-e5f6-7890-abcd-ef1234567890', '台北市中山區南京東路3段123號', '0987654321', 'credit_card', 'none', 1, 19000, NULL, CURRENT_TIMESTAMP - INTERVAL '26 days', CURRENT_TIMESTAMP - INTERVAL '26 days'),
('extra-order-11', 'c3d4e5f6-7890-abcd-ef12-34567890abcd', '台中市西區公益路321巷9號', '0987654321', 'credit_card', 'none', 1, 9500, NULL, CURRENT_TIMESTAMP - INTERVAL '25 days', CURRENT_TIMESTAMP - INTERVAL '25 days'),
('extra-order-12', 'b2c3d4e5-f678-90ab-cdef-234567890abc', '高雄市鼓山區美術館路45號', '0912345678', 'credit_card', 'none', 1, 22000, NULL, CURRENT_TIMESTAMP - INTERVAL '24 days', CURRENT_TIMESTAMP - INTERVAL '24 days'),
('extra-order-13', 'b2c3d4e5-f678-90ab-cdef-234567890abc', '高雄市鼓山區美術館路45號', '0912345678', 'credit_card', 'point', 1, 18000, 17600, CURRENT_TIMESTAMP - INTERVAL '23 days', CURRENT_TIMESTAMP - INTERVAL '23 days'),
('extra-order-14', 'c3d4e5f6-7890-abcd-ef12-34567890abcd', '台中市西區公益路321巷9號', '0987654321', 'credit_card', 'none', 1, 9000, NULL, CURRENT_TIMESTAMP - INTERVAL '22 days', CURRENT_TIMESTAMP - INTERVAL '22 days'),
('extra-order-15', 'a1b2c3d4-e5f6-7890-abcd-ef1234567890', '台北市中山區南京東路3段123號', '0987654321', 'credit_card', 'none', 1, 17600, NULL, CURRENT_TIMESTAMP - INTERVAL '21 days', CURRENT_TIMESTAMP - INTERVAL '21 days'),
('extra-order-16', 'a1b2c3d4-e5f6-7890-abcd-ef1234567890', NULL, NULL, NULL, NULL, -1, 72000, NULL, CURRENT_TIMESTAMP - INTERVAL '20 days', CURRENT_TIMESTAMP - INTERVAL '20 days'),
('extra-order-17', 'b2c3d4e5-f678-90ab-cdef-234567890abc', '高雄市鼓山區美術館路45號', '0912345678', 'atm', 'none', 0, 15000, NULL, CURRENT_TIMESTAMP - INTERVAL '19 days', CURRENT_TIMESTAMP - INTERVAL '19 days'),
('extra-order-18', 'c3d4e5f6-7890-abcd-ef12-34567890abcd', '台中市西區公益路321巷9號', '0987654321', 'credit_card', 'none', 2, 85000, NULL, CURRENT_TIMESTAMP - INTERVAL '18 days', CURRENT_TIMESTAMP - INTERVAL '18 days'),
('extra-order-19', 'c3d4e5f6-7890-abcd-ef12-34567890abcd', '台中市西區公益路321巷9號', '0987654321', 'credit_card', 'none', 3, 22000, NULL, CURRENT_TIMESTAMP - INTERVAL '17 days', CURRENT_TIMESTAMP - INTERVAL '17 days'),
('extra-order-20', 'a1b2c3d4-e5f6-7890-abcd-ef1234567890', '台北市中山區南京東路3段123號', '0987654321', 'cvs', 'none', 4, 85000, NULL, CURRENT_TIMESTAMP - INTERVAL '16 days', CURRENT_TIMESTAMP - INTERVAL '16 days');

---- 18. 訂單細項資料 "order_item"（取代來源檔的 10 列）
INSERT INTO order_item (order_item_id, order_id, tour_id, total_price, discount_price, payment_status, quantity, start_date, end_date, room_type, created_at, updated_at) VALUES
(uuid_generate_v4(), 'extra-order-01', '11111111-aaaa-bbbb-cccc-111111111111', 45000, 40500, 1, 1, '2025-12-01 00:00:00', '2025-12-05 23:59:59', NULL, CURRENT_TIMESTAMP - INTERVAL '9 days', CURRENT_TIMESTAMP - INTERVAL '9 days'),
(uuid_generate_v4(), 'extra-order-02', '11111111-aaaa-bbbb-cccc-111111111111', 45000, 40500, 1, 1, '2025-12-01 00:00:00', '2025-12-05 23:59:59', NULL, CURRENT_TIMESTAMP - INTERVAL '8 days', CURRENT_TIMESTAMP - INTERVAL '8 days'),
(uuid_generate_v4(), 'extra-order-03', '11111111-aaaa-bbbb-cccc-111111111111', 45000, 40500, 1, 1, '2025-12-01 00:00:00', '2025-12-05 23:59:59', NULL, CURRENT_TIMESTAMP - INTERVAL '7 days', CURRENT_TIMESTAMP - INTERVAL '7 days'),
(uuid_generate_v4(), 'extra-order-04', '22222222-bbbb-cccc-dddd-222222222222', 98000, 83300, 1, 1, '2025-11-10 00:00:00', '2025-11-15 23:59:59', NULL, CURRENT_TIMESTAMP - INTERVAL '4 days', CURRENT_TIMESTAMP - INTERVAL '4 days'),
(uuid_generate_v4(), 'extra-order-05', '22222222-bbbb-cccc-dddd-222222222222', 98000, 83300, 1, 1, '2025-11-10 00:00:00', '2025-11-15 23:59:59', NULL, CURRENT_TIMESTAMP - INTERVAL '3 days', CURRENT_TIMESTAMP - INTERVAL '3 days'),
(uuid_generate_v4(), 'extra-order-06', '00000000-dddd-eeee-ffff-000000000000', 85000, NULL, 1, 1, '2025-11-05 00:00:00', '2025-11-15 23:59:59', NULL, CURRENT_TIMESTAMP - INTERVAL '30 days', CURRENT_TIMESTAMP - INTERVAL '30 days'),
(uuid_generate_v4(), 'extra-order-07', '99999999-cccc-dddd-eeee-999999999999', 8400, NULL, 1, 2, '2025-06-19', NULL, NULL, CURRENT_TIMESTAMP - INTERVAL '29 days', CURRENT_TIMESTAMP - INTERVAL '29 days'),
(uuid_generate_v4(), 'extra-order-08', '99999999-cccc-dddd-eeee-999999999999', 12600, NULL, 1, 3, '2025-06-19', NULL, NULL, CURRENT_TIMESTAMP - INTERVAL '28 days', CURRENT_TIMESTAMP - INTERVAL '28 days'),
(uuid_generate_v4(), 'extra-order-09', '33333333-cccc-dddd-eeee-333333333333', 30000, NULL, 1, 2, '2025-06-19', NULL, NULL, CURRENT_TIMESTAMP - INTERVAL '27 days', CURRENT_TIMESTAMP - INTERVAL '27 days'),
(uuid_generate_v4(), 'extra-order-10', '77777777-aaaa-bbbb-cccc-777777777777', 19000, NULL, 1, 2, '2025-06-19', NULL, NULL, CURRENT_TIMESTAMP - INTERVAL '26 days', CURRENT_TIMESTAMP - INTERVAL '26 days'),
(uuid_generate_v4(), 'extra-order-11', '77777777-aaaa-bbbb-cccc-777777777777', 9500, NULL, 1, 1, '2025-06-19', NULL, NULL, CURRENT_TIMESTAMP - INTERVAL '25 days', CURRENT_TIMESTAMP - INTERVAL '25 days'),
(uuid_generate_v4(), 'extra-order-12', '44444444-dddd-eeee-ffff-444444444444', 22000, NULL, 1, 1, '2025-06-19', NULL, NULL, CURRENT_TIMESTAMP - INTERVAL '24 days', CURRENT_TIMESTAMP - INTERVAL '24 days'),
(uuid_generate_v4(), 'extra-order-13', '55555555-eeee-ffff-aaaa-555555555555', 18000, NULL, 1, 2, '2025-06-19', '2025-06-21', '設計雙人房', CURRENT_TIMESTAMP - INTERVAL '23 days', CURRENT_TIMESTAMP - INTERVAL '23 days'),
(uuid_generate_v4(), 'extra-order-14', '55555555-eeee-ffff-aaaa-555555555555', 9000, NULL, 1, 1, '2025-06-19', '2025-06-21', '設計雙人房', CURRENT_TIMESTAMP - INTERVAL '22 days', CURRENT_TIMESTAMP - INTERVAL '22 days'),
(uuid_generate_v4(), 'extra-order-15', 'extra-tour-10', 17600, NULL, 1, 2, '2025-06-19', '2025-06-21', '海景雙人房', CURRENT_TIMESTAMP - INTERVAL '21 days', CURRENT_TIMESTAMP - INTERVAL '21 days'),
(uuid_generate_v4(), 'extra-order-16', '66666666-ffff-aaaa-bbbb-666666666666', 72000, NULL, -1, 1, '2025-10-15 00:00:00', '2025-10-22 23:59:59', NULL, CURRENT_TIMESTAMP - INTERVAL '20 days', CURRENT_TIMESTAMP - INTERVAL '20 days'),
(uuid_generate_v4(), 'extra-order-17', '33333333-cccc-dddd-eeee-333333333333', 15000, NULL, 0, 1, '2025-06-19', NULL, NULL, CURRENT_TIMESTAMP - INTERVAL '19 days', CURRENT_TIMESTAMP - INTERVAL '19 days'),
(uuid_generate_v4(), 'extra-order-18', '00000000-dddd-eeee-ffff-000000000000', 85000, NULL, 2, 1, '2025-11-05 00:00:00', '2025-11-15 23:59:59', NULL, CURRENT_TIMESTAMP - INTERVAL '18 days', CURRENT_TIMESTAMP - INTERVAL '18 days'),
(uuid_generate_v4(), 'extra-order-19', '44444444-dddd-eeee-ffff-444444444444', 22000, NULL, 3, 1, '2025-06-19', NULL, NULL, CURRENT_TIMESTAMP - INTERVAL '17 days', CURRENT_TIMESTAMP - INTERVAL '17 days'),
(uuid_generate_v4(), 'extra-order-20', '00000000-dddd-eeee-ffff-000000000000', 85000, NULL, 4, 1, '2025-11-05 00:00:00', '2025-11-15 23:59:59', NULL, CURRENT_TIMESTAMP - INTERVAL '16 days', CURRENT_TIMESTAMP - INTERVAL '16 days');

---- 19. 付款紀錄資料 "payment"
INSERT INTO payment (payment_id, user_id, order_id, address, phone, payment_method, payment_status, discount_price, return_data, return_time, result_info, result_time) VALUES
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567890', 'extra-order-01', '台北市中山區南京東路3段123號', '0987654321', 'credit_card', 1, NULL, NULL, CURRENT_TIMESTAMP, '付款成功', CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'b2c3d4e5-f678-90ab-cdef-234567890abc', 'extra-order-02', '高雄市鼓山區美術館路45號', '0912345678', 'credit_card', 1, 44990, NULL, CURRENT_TIMESTAMP, '付款成功', CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'c3d4e5f6-7890-abcd-ef12-34567890abcd', 'extra-order-03', '台中市西區公益路321巷9號', '0987654321', 'credit_card', 1, NULL, NULL, CURRENT_TIMESTAMP, '付款成功', CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567890', 'extra-order-04', '台北市中山區南京東路3段123號', '0987654321', 'credit_card', 1, 97700, NULL, CURRENT_TIMESTAMP, '付款成功', CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'c3d4e5f6-7890-abcd-ef12-34567890abcd', 'extra-order-05', '台中市西區公益路321巷9號', '0987654321', 'atm', 1, NULL, NULL, CURRENT_TIMESTAMP, '付款成功', CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'b2c3d4e5-f678-90ab-cdef-234567890abc', 'extra-order-06', '高雄市鼓山區美術館路45號', '0912345678', 'credit_card', 1, 84700, NULL, CURRENT_TIMESTAMP, '付款成功', CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567890', 'extra-order-07', '台北市中山區南京東路3段123號', '0987654321', 'credit_card', 1, 8200, NULL, CURRENT_TIMESTAMP, '付款成功', CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'b2c3d4e5-f678-90ab-cdef-234567890abc', 'extra-order-08', '高雄市鼓山區美術館路45號', '0912345678', 'cvs', 1, NULL, NULL, CURRENT_TIMESTAMP, '付款成功', CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'c3d4e5f6-7890-abcd-ef12-34567890abcd', 'extra-order-09', '台中市西區公益路321巷9號', '0987654321', 'credit_card', 1, 29680, NULL, CURRENT_TIMESTAMP, '付款成功', CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567890', 'extra-order-10', '台北市中山區南京東路3段123號', '0987654321', 'credit_card', 1, NULL, NULL, CURRENT_TIMESTAMP, '付款成功', CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'c3d4e5f6-7890-abcd-ef12-34567890abcd', 'extra-order-11', '台中市西區公益路321巷9號', '0987654321', 'credit_card', 1, NULL, NULL, CURRENT_TIMESTAMP, '付款成功', CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'b2c3d4e5-f678-90ab-cdef-234567890abc', 'extra-order-12', '高雄市鼓山區美術館路45號', '0912345678', 'credit_card', 1, NULL, NULL, CURRENT_TIMESTAMP, '付款成功', CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'b2c3d4e5-f678-90ab-cdef-234567890abc', 'extra-order-13', '高雄市鼓山區美術館路45號', '0912345678', 'credit_card', 1, 17600, NULL, CURRENT_TIMESTAMP, '付款成功', CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'c3d4e5f6-7890-abcd-ef12-34567890abcd', 'extra-order-14', '台中市西區公益路321巷9號', '0987654321', 'credit_card', 1, NULL, NULL, CURRENT_TIMESTAMP, '付款成功', CURRENT_TIMESTAMP),
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567890', 'extra-order-15', '台北市中山區南京東路3段123號', '0987654321', 'credit_card', 1, NULL, NULL, CURRENT_TIMESTAMP, '付款成功', CURRENT_TIMESTAMP);

---- 20. 評論資料 "review"（新增 3 則 web）
INSERT INTO "review" (review_id, user_id, tour_id, type, hashtag, rating, content, created_at, updated_at) VALUES
(uuid_generate_v4(), 'c3d4e5f6-7890-abcd-ef12-34567890abcd', NULL, 'web', '#介面清爽', 5, '行程搜尋很好用，收藏功能也很方便。', CURRENT_TIMESTAMP - INTERVAL '3 days', CURRENT_TIMESTAMP - INTERVAL '3 days'),
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567890', NULL, 'web', '#資訊完整', 4, '商品頁的資訊很完整，比價很省時間。', CURRENT_TIMESTAMP - INTERVAL '2 days', CURRENT_TIMESTAMP - INTERVAL '2 days'),
(uuid_generate_v4(), 'b2c3d4e5-f678-90ab-cdef-234567890abc', NULL, 'web', '#客服親切', 5, '訂單有問題時客服回覆很快。', CURRENT_TIMESTAMP - INTERVAL '1 days', CURRENT_TIMESTAMP - INTERVAL '1 days');

---- 23. 使用者收藏旅遊商品 "favorite"（新增 2 筆）
INSERT INTO "favorite" (favorite_id, user_id, tour_id, created_at, updated_at) VALUES
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567890', '11111111-aaaa-bbbb-cccc-111111111111', CURRENT_TIMESTAMP - INTERVAL '1 days', CURRENT_TIMESTAMP - INTERVAL '1 days'),
(uuid_generate_v4(), 'b2c3d4e5-f678-90ab-cdef-234567890abc', '22222222-bbbb-cccc-dddd-222222222222', CURRENT_TIMESTAMP - INTERVAL '2 days', CURRENT_TIMESTAMP - INTERVAL '2 days');

---- 24. 會員旅遊積分資料 "point_record"（取代來源檔的 2 列）
INSERT INTO point_record (point_id, user_id, order_id, type, point) VALUES
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567890', 'extra-order-01', '新增', 4500),
(uuid_generate_v4(), 'b2c3d4e5-f678-90ab-cdef-234567890abc', 'extra-order-02', '新增', 4500),
(uuid_generate_v4(), 'c3d4e5f6-7890-abcd-ef12-34567890abcd', 'extra-order-03', '新增', 4500),
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567890', 'extra-order-04', '新增', 9800),
(uuid_generate_v4(), 'c3d4e5f6-7890-abcd-ef12-34567890abcd', 'extra-order-05', '新增', 9800),
(uuid_generate_v4(), 'b2c3d4e5-f678-90ab-cdef-234567890abc', 'extra-order-06', '新增', 8500),
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567890', 'extra-order-07', '新增', 840),
(uuid_generate_v4(), 'b2c3d4e5-f678-90ab-cdef-234567890abc', 'extra-order-08', '新增', 1260),
(uuid_generate_v4(), 'c3d4e5f6-7890-abcd-ef12-34567890abcd', 'extra-order-09', '新增', 3000),
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567890', 'extra-order-10', '新增', 1900),
(uuid_generate_v4(), 'c3d4e5f6-7890-abcd-ef12-34567890abcd', 'extra-order-11', '新增', 950),
(uuid_generate_v4(), 'b2c3d4e5-f678-90ab-cdef-234567890abc', 'extra-order-12', '新增', 2200),
(uuid_generate_v4(), 'b2c3d4e5-f678-90ab-cdef-234567890abc', 'extra-order-13', '新增', 1800),
(uuid_generate_v4(), 'c3d4e5f6-7890-abcd-ef12-34567890abcd', 'extra-order-14', '新增', 900),
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567890', 'extra-order-15', '新增', 1760),
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567890', 'extra-order-07', '減少', -250),
(uuid_generate_v4(), 'c3d4e5f6-7890-abcd-ef12-34567890abcd', 'extra-order-09', '減少', -400),
(uuid_generate_v4(), 'b2c3d4e5-f678-90ab-cdef-234567890abc', 'extra-order-13', '減少', -500);
