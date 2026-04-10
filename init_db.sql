-- MySQL dump 10.13  Distrib 8.0.43, for Win64 (x86_64)
--
-- Host: 127.0.0.1    Database: plant_db
-- ------------------------------------------------------
-- Server version	8.0.43

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `crop`
--

DROP TABLE IF EXISTS `crop`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `crop` (
  `crop_id` int NOT NULL AUTO_INCREMENT,
  `crop_name` varchar(100) DEFAULT NULL,
  `crop_name_en` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`crop_id`)
) ENGINE=InnoDB AUTO_INCREMENT=841 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `crop`
--

/*!40000 ALTER TABLE `crop` DISABLE KEYS */;
INSERT INTO `crop` VALUES (1,'甜椒','Bell Pepper'),(2,'萵苣','Lettuce'),(3,'甜瓜','Melon'),(4,'西瓜','Watermelon'),(5,'薑','Ginger'),(6,'玉米百合','Corn Lily'),(7,'玉米','Corn'),(8,'辣椒','Chili'),(9,'觀賞辣椒','Ornamental Peppers'),(10,'豌豆芽菜','Pea Sprouts'),(11,'豌豆','Pea'),(12,'玉米筍','Corn Shoots'),(13,'檬果','Lemon Fruit'),(14,'甘藍','Cabbage'),(15,'樹番茄','Tamarillo'),(16,'青油菜','Green Rape'),(17,'紅龍果','Red Dragon Fruit'),(18,'馬拉巴栗','Malabar Chestnut'),(19,'菊花','Chrysanthemum'),(20,'火鶴','Flamingo'),(21,'玫瑰','Rose'),(22,'劍蘭','Gladiolus'),(23,'百合','Lily'),(24,'其他蘭花','Other Orchids'),(25,'小花蕙蘭','Cymbidium'),(26,'虎頭蘭','Tiger Head Orchid'),(27,'嘉德麗雅蘭','Cattleya Orchid'),(28,'仙履蘭','Cinderella'),(29,'石斛蘭','Dendrobium'),(30,'文心蘭','Oncidium'),(31,'蝴蝶蘭','Phalaenopsis'),(32,'其他景觀作物','Other Landscape Crops'),(33,'景觀小油菊','Landscape Chrysanthemum'),(34,'景觀萬壽菊','Landscape Marigold'),(35,'景觀波斯菊','Landscape Cosmos'),(36,'景觀向日葵','Landscape Sunflower'),(37,'其他綠肥作物','Other Green Manure Crops'),(38,'魯冰','Lu Bing'),(39,'青皮豆','Green Beans'),(40,'鐵虎豆','Iron Tiger Bean'),(41,'苕子','Sweet Potato'),(42,'紫雲英','Milk Vetch'),(43,'田菁','Sesbania'),(44,'爬地蘭','Creeping Ground Orchid'),(45,'富貴豆','Rich Beans'),(46,'太陽麻','Sun Hemp'),(47,'大豆類','Soy Beans'),(48,'大菜','Dish'),(49,'埃及三葉草',NULL),(50,'其他牧草','Other Pastures'),(51,'其他長期牧草','Other Long-Term Pastures'),(52,'其他短期牧草','Other Short-Term Pasture'),(53,'青割玉米','Green Cut Corn'),(54,'蘇丹草','Sudan Grass'),(55,'苜蓿草','Alfalfa'),(56,'盤固拉草','Pangu Lacao'),(57,'狼尾草','Pennisetum'),(58,'尼羅草','Nile Grass'),(59,'酒類製品','Liquor Products'),(60,'蜂產品','Bee Products'),(61,'綜合蔬果製品','Comprehensive Fruit And Vegetable Products'),(62,'其他特用作物加工製品','Other Special Crop Processing Products'),(63,'胡麻製品','Flax Products'),(64,'薑黃製品','Turmeric Products'),(65,'愛玉製品','Love Jade Products'),(66,'茶製品','Tea Products'),(67,'油茶製品','Camellia Oleifera Products'),(68,'洛神葵製品','Roselle Products'),(69,'香茅製品','Citronella Products'),(70,'甘蔗製品','Sugarcane Products'),(71,'咖啡製品','Coffee Products'),(72,'梔子製品','Gardenia Products'),(73,'諾麗果製品','Noni Fruit Products'),(74,'風茹製品','Fengru Products'),(75,'甜菊製品','Stevia Products'),(76,'杭菊製品','Hangju Products'),(77,'向日葵製品','Sunflower Products'),(78,'仙草製品','Grass Jelly Products'),(79,'紫蘇製品','Perilla Products'),(80,'其他花卉加工製品','Other Flower Processed Products'),(81,'油菊製品','Chrysanthemum Products'),(82,'茉莉花製品','Jasmine Products'),(83,'玫瑰花製品','Rose Products'),(84,'其他水果加工製品','Other Fruit Processed Products'),(85,'可可製品','Cocoa Products'),(86,'栗子製品','Chestnut Products'),(87,'椰子製品','Coconut Products'),(88,'橄欖製品','Olive Products'),(89,'棗製品','Jujube Products'),(90,'梅製品','Plum Products'),(91,'李製品','Li Products'),(92,'桃製品','Peach Products'),(93,'芒果製品','Mango Products'),(94,'龍眼製品','Longan Products'),(95,'荔枝製品','Lychee Products'),(96,'枇杷製品','Loquat Products'),(97,'梨製品','Pear Products'),(98,'蘋果製品','Apple Products'),(99,'木鱉果製品','Wood Turtle Fruit Products'),(100,'楊梅製品','Bayberry Products'),(101,'榴槤蜜製品','Durian Honey Products'),(102,'桑椹製品','Mulberry Products'),(103,'波羅蜜製品','Jackfruit Products'),(104,'柿製品','Persimmon Products'),(105,'釋迦製品','Custard Apple Products'),(106,'奇異果製品','Kiwi Products'),(107,'紅龍果製品','Red Dragon Fruit Products'),(108,'百香果製品','Passion Fruit Products'),(109,'楊桃製品','Star Fruit Products'),(110,'葡萄製品','Grape Products'),(111,'蓮霧製品','Lotus Mist Products'),(112,'番石榴製品','Guava Products'),(113,'鳳梨製品','Pineapple Products'),(114,'香蕉製品','Banana Products'),(115,'木瓜製品','Papaya Products'),(116,'金柑製品','Kumquat Products'),(117,'檸檬製品','Lemon Products'),(118,'柑橘製品','Citrus Products'),(119,'椪柑製品','Ponkan Products'),(120,'柳橙製品','Orange Products'),(121,'葡萄柚製品','Grapefruit Products'),(122,'柚子製品','Grapefruit Products'),(123,'其他蔬菜加工製品','Other Vegetable Processed Products'),(124,'白木耳製品','White Fungus Products'),(125,'黑木耳製品','Black Fungus Products'),(126,'猴頭菇製品','Hericium Products'),(127,'杏鮑菇製品','King Oyster Mushroom Products'),(128,'香菇製品','Mushroom Products'),(129,'草莓製品','Strawberry Products'),(130,'黃秋葵製品','Okra Products'),(131,'菱角製品','Water Chestnut Products'),(132,'番茄製品','Tomato Products'),(133,'辣椒製品','Chili Products'),(134,'甜瓜製品','Melon Products'),(135,'西瓜製品','Watermelon Products'),(136,'越瓜製品','Viet Melon Products'),(137,'苦瓜製品','Bitter Melon Products'),(138,'胡瓜製品','Courgette Products'),(139,'絲瓜製品','Luffa Products'),(140,'南瓜製品','Pumpkin Products'),(141,'冬瓜製品','Winter Melon Products'),(142,'蠶豆製品','Broad Bean Products'),(143,'豌豆製品','Pea Products'),(144,'花豆製品','Pinto Products'),(145,'毛豆製品','Edamame Products'),(146,'金針花製品','Daylily Flower Products'),(147,'胡蘿蔔製品','Carrot Products'),(148,'牛蒡製品','Burdock Products'),(149,'蘿蔔製品','Radish Products'),(150,'馬鈴薯製品','Potato Products'),(151,'山藥製品','Yam Products'),(152,'山葵製品','Wasabi Products'),(153,'蘆筍製品','Asparagus Products'),(154,'薑製品','Ginger Products'),(155,'芋頭製品','Taro Products'),(156,'蓮藕製品','Lotus Root Products'),(157,'竹筍製品','Bamboo Shoot Products'),(158,'食用百合製品','Edible Lily Products'),(159,'洋蔥製品','Onion Products'),(160,'蔥製品','Onion Products'),(161,'蒜製品','Garlic Products'),(162,'羅勒製品','Basil Products'),(163,'菠菜製品','Spinach Products'),(164,'芹菜製品','Celery Products'),(165,'芥菜製品','Mustard Products'),(166,'油菜製品','Rapeseed Products'),(167,'結球白菜製品','Cabbage Products'),(168,'甘藍製品','Cabbage Products'),(169,'其他五穀雜糧加工製品','Other Processed Grain Products'),(170,'木薯製品','Cassava Products'),(171,'甘藷製品','Sweet Potato Products'),(172,'綠豆製品','Mung Bean Products'),(173,'紅豆製品','Red Bean Products'),(174,'落花生製品','Peanut Products'),(175,'大豆製品','Soy Products'),(176,'薏苡製品','Coix Products'),(177,'燕麥製品','Oat Products'),(178,'蕎麥製品','Buckwheat Products'),(179,'大麥製品','Barley Products'),(180,'高粱製品','Sorghum Products'),(181,'小米製品','Millet Products'),(182,'小麥製品','Wheat Products'),(183,'玉米製品','Corn Products'),(184,'硬質玉米製品','Hard Corn Products'),(185,'稻米製品','Rice Products'),(186,'其他特用作物','Other Specialty Crops'),(187,'其他長期特作','Other Long-Term Special Works'),(188,'其他短期特作','Other Short-Term Special Projects'),(189,'其他飲料作物','Other Beverage Crops'),(190,'愛玉子','Ai Yuzi'),(191,'茶','Tea'),(192,'洛神','Luo Shen'),(193,'咖啡','Coffee'),(194,'杭菊','Hang Ju'),(195,'仙草','Grass Jelly'),(196,'其他香料作物','Other Spice Crops'),(197,'香水蓮','Perfume Lotus'),(198,'香草','Vanilla'),(199,'秀英','Xiuying'),(200,'茉莉花_薰芬茶用','Jasmine_For Xunfen Tea'),(201,'桂花','Osmanthus Fragrans'),(202,'檸檬香茅','Lemongrass'),(203,'香茅','Lemongrass'),(204,'蒔蘿','Dill'),(205,'芳香萬壽菊','Fragrant Marigold'),(206,'薄荷','Mint'),(207,'紫蘇','Perilla'),(208,'其他澱粉作物','Other Starch Crops'),(209,'紅蓮蕉','Red Lotus Banana'),(210,'蒟蒻','Konjac'),(211,'葛鬱金','Ge Yujin'),(212,'葛藤','Kudzu'),(213,'其他染料作物','Other Dye Crops'),(214,'薑黃','Turmeric'),(215,'大菁','Dajing'),(216,'藷茛','Buttercups'),(217,'梔子','Gardenia'),(218,'大青','Daqing'),(219,'紅花','Safflower'),(220,'其他纖維作物','Other Fiber Crops'),(221,'瓊麻','Qionma'),(222,'亞麻','Flax'),(223,'圓藺草','Round Rush'),(224,'苧麻','Ramie'),(225,'大甲藺','Dajialin'),(226,'三角藺','Triangle Lin'),(227,'棉花','Cotton'),(228,'貴黍','Expensive Millet'),(229,'其他糖料作物','Other Sugar Crops'),(230,'甘蔗','Sugar Cane'),(231,'甜菊','Stevia'),(232,'其他嗜好作物','Other Hobby Crops'),(233,'菸草','Tobacco'),(234,'荖藤','Vine'),(235,'荖葉','Lilac Leaves'),(236,'荖花','Lihua'),(237,'其他油料作物','Other Oil Crops'),(238,'胡麻','Flax'),(239,'小果種油茶','Camellia Oleifera'),(240,'大果種油茶','Camellia Oleifera With Big Fruit'),(241,'向日葵_採種供作加工原料','Sunflower_Seeds Collected For Processing Raw Materials'),(242,'其他藥用作物','Other Medicinal Crops'),(243,'杜虹花','Du Honghua'),(244,'白花蛇舌草','Hedyotis Diffusa'),(245,'桋梧','桋武'),(246,'假人參','Fake Ginseng'),(247,'蕺菜','Amaranth'),(248,'辣木','Moringa'),(249,'山葡萄','Mountain Grape'),(250,'地黃','Rehmannia Glutinosa'),(251,'七葉膽','Aesculus'),(252,'澤瀉','Alisma'),(253,'白果','Ginkgo'),(254,'香椿','Toon'),(255,'小葉藜','Chenopodium Lobata'),(256,'何首烏','Polygonum Multiflorum'),(257,'南薑','Galangal'),(258,'羊奶頭','Goat Teats'),(259,'土肉桂','Earth Cinnamon'),(260,'肉桂','Cinnamon'),(261,'桔梗','Platycodon'),(262,'黨蔘','Ginseng'),(263,'青葙','Qinghui'),(264,'法國綠莧','French Green Amaranth'),(265,'金線蓮','Anomatis'),(266,'刺五加','Acanthopanax'),(267,'蓪草','Cordyceps'),(268,'山芙蓉','Mountain Hibiscus'),(269,'圓葉錦葵','Round-Leaf Mallow'),(270,'穿心蓮','Andrographis Paniculata'),(271,'白鶴靈芝','White Crane Ganoderma Lucidum'),(272,'麥門冬','Ophiopogon Japonicus'),(273,'蘆薈','Aloe Vera'),(274,'白藷莨','White Dioscorea'),(275,'枸杞','Wolfberry'),(276,'葉用枸杞','Lycium Barbarum Leaves'),(277,'諾麗果','Noni Fruit'),(278,'桑黃','Phellinus Mulberry'),(279,'茯苓','Poria'),(280,'樟芝','Antrodia Camphorata'),(281,'槐耳','Huaier'),(282,'通天草','Babel'),(283,'黃耆','Huang Qi'),(284,'當歸','Angelica Sinensis'),(285,'柴胡','Bupleurum'),(286,'明日葉','Ashitaba'),(287,'艾草','Mugwort'),(288,'小金英','Xiao Jinying'),(289,'蒲公英','Dandelion'),(290,'風茹草','Feng Rucao'),(291,'傷寒草','Typhoid Grass'),(292,'六神花','Liushenhua'),(293,'除蟲菊','Pyrethrum'),(294,'澤蘭','Zeeland'),(295,'款冬','Coltsfoot'),(296,'山防風','Mountain Windbreak'),(297,'荊芥','Nepeta'),(298,'筋骨草','Muscle Grass'),(299,'半支蓮','Half Lotus'),(300,'丹參','Salvia'),(301,'黃芩','Skullcap'),(302,'益母草','Motherwort'),(303,'草石蠶','Grass Caddis'),(304,'其他雜糧','Other Cereals'),(305,'其他藷類','Other Potatoes'),(306,'木薯','Cassava'),(307,'甘藷','Sweet Potato'),(308,'其他穀類','Other Cereals'),(309,'臺灣藜','Taiwan Quinoa'),(310,'高粱','Sorghum'),(311,'薏苡','Coix'),(312,'蕎麥','Buckwheat'),(313,'燕麥','Oat'),(314,'小麥','Wheat'),(315,'小米','Millet'),(316,'大麥','Barley'),(317,'其他豆類','Other Legumes'),(318,'樹豆','Tree Beans'),(319,'落花生','Peanut'),(320,'米豆','Rice Beans'),(321,'綠豆','Green Beans'),(322,'紅豆','Red Beans'),(323,'大豆','Soybeans'),(324,'珠廉','Zhulian'),(325,'鳳尾草','Ferns'),(326,'高山羊齒','Alpine Goat Tooth'),(327,'腎蕨','Kidney Fern'),(328,'石蓮','Echeveria'),(329,'山蘇','Shansu'),(330,'虎尾蘭','Sansevieria'),(331,'常春藤','Ivy'),(332,'蔓綠絨','Philodendron'),(333,'電信蘭','Telecom Lan'),(334,'黃金葛','Golden Kudzu'),(335,'其他多年生草本','Other Perennial Herbs'),(336,'球薑','Ball Ginger'),(337,'火炬花','Torch Flower'),(338,'野薑花','Wild Ginger Flower'),(339,'薑荷花','Ginger Lotus'),(340,'月桃','Yuetao'),(341,'水蠟燭','Water Candle'),(342,'天堂鳥','Bird Of Paradise'),(343,'聖誕果','Christmas Fruit'),(344,'牛頭茄','Taurus'),(345,'金魚草','Snapdragon'),(346,'泡盛草','Awamori'),(347,'陸蓮花','Lu Lianhua'),(348,'飛燕草','Delphinium'),(349,'夢幻草','Dream Grass'),(350,'白頭翁','Pulsatilla'),(351,'銀蘆','Silver Reed'),(352,'星辰花','Star Flower'),(353,'豇豆','Cowpea'),(354,'蠶豆','Broad Bean'),(355,'翼豆','Winged Beans'),(356,'萊豆','Laidou'),(357,'鵲豆','Magpie Beans'),(358,'毛豆','Edamame'),(359,'刀豆','Sword Bean'),(360,'菜豆','Kidney Bean'),(361,'其他花菜苗','Other Cauliflower Seedlings'),(362,'其他花菜','Other Cauliflower'),(363,'金針花','Daylily Flower'),(364,'石蓮花','Echeveria'),(365,'朝鮮薊','Artichoke'),(366,'青花菜','Broccoli'),(367,'花椰菜','Cauliflower'),(368,'其他根菜','Other Root Vegetables'),(369,'胡蘿蔔','Carrot'),(370,'甜菜根','Beetroot'),(371,'闊葉大豆','Broadleaf Soybeans'),(372,'豆薯','Yam Bean'),(373,'雪蓮薯','Snow Lotus Potato'),(374,'辣根','Horseradish'),(375,'瑞典蕪菁','Swedish Turnip'),(376,'蘿蔔','Radish'),(377,'其他莖菜','Other Stem Vegetables'),(378,'仙人掌肉質莖','Cactus Fleshy Stem'),(379,'碧玉筍','Jasper Bamboo Shoots'),(380,'晚香玉筍','Tuberose Bamboo Shoots'),(381,'食用大黃','Edible Rhubarb'),(382,'水蓮','Water Lily'),(383,'薯蕷','Dioscorea'),(384,'荸薺','Water Chestnuts'),(385,'蓴菜','Water Shield'),(386,'馬鈴薯','Potato'),(387,'慈菇','Cigu'),(388,'萵苣莖','Lettuce Stems'),(389,'菊芋','Jerusalem Artichoke'),(390,'黃藤心','Yellow Vine Heart'),(391,'半天筍','Half-Day Bamboo Shoots'),(392,'山葵','Wasabi'),(393,'球莖甘藍','Kohlrabi'),(394,'蘆筍','Asparagus'),(395,'蘘荷','Xinhe'),(396,'芋','Taro'),(397,'蓮','Lotus'),(398,'茭白筍','Wild Bamboo Shoots'),(399,'甘蔗筍','Sugar Cane Bamboo Shoots'),(400,'牧草筍','Pasture Bamboo Shoots'),(401,'竹筍','Bamboo Shoots'),(402,'其他鱗莖','Other Bulbs'),(403,'食用百合','Edible Lily'),(404,'蝦夷蔥','Shrimp And Green Onions'),(405,'蕎頭','Buckwheat Head'),(406,'洋蔥','Onion'),(407,'韭蔥','Leek'),(408,'分蔥','Divide Onions'),(409,'蔥','Onion'),(410,'蒜頭','Garlic'),(411,'大蒜','Garlic'),(412,'其他葉菜苗','Other Leafy Vegetable Seedlings'),(413,'其他葉菜','Other Leafy Vegetables'),(414,'麻意','Numbness'),(415,'糯米糰','Glutinous Rice Balls'),(416,'龍葵','Nightshade'),(417,'食茱萸','Eat Cornus Officinalis'),(418,'學菜','Learn Cooking'),(419,'水合歡','Acacia'),(420,'過溝菜蕨','Bracken Fern'),(421,'龍鳳草','Dragon Phoenix Grass'),(422,'人蔘菜','Ginseng'),(423,'馬齒莧','Purslane'),(424,'番杏','Apricot'),(425,'冰花','Ice Flower'),(426,'羅勒','Basil'),(427,'山菠菜','Mountain Spinach'),(428,'葉用甘藷','Leaf Sweet Potato'),(429,'蕹菜','Water Spinach'),(430,'藤三七','Fujisanchi'),(431,'落葵','Luokui'),(432,'韭菜','Chinese Chives'),(433,'菾菜','Chinese Cabbage'),(434,'菠菜','Spinach'),(435,'莧菜','Amaranth'),(436,'香芹菜','Parsley'),(437,'水芹','Cress'),(438,'茴香','Fennel'),(439,'刺芹','Eryngium'),(440,'芫荽','Coriander'),(441,'芹菜','Celery'),(442,'闊苞菊','Brachyphyllum'),(443,'白鳳菜','White Cabbage'),(444,'紅鳳菜','Red Cabbage'),(445,'茼蒿','Chrysanthemum'),(446,'山茼蒿','Mountain Chrysanthemum'),(447,'吉康菜','Jikang Cuisine'),(448,'苦苣','Chicory'),(449,'珍珠菜','Loosestrife'),(450,'葉用蘿蔔','Leaf With Radish'),(451,'西洋菜','Watercress'),(452,'芝麻菜','Arugula'),(453,'薺菜','Shepherd\'S Purse'),(454,'千寶菜','Qianbaocai'),(455,'油江菜','Youjiang Vegetable'),(456,'廣島菜','Hiroshima Food'),(457,'青菘菜','Green Cabbage'),(458,'小菘菜','Baby Cabbage'),(459,'菜心','Choi Sum'),(460,'水菜','Mizuna'),(461,'塌棵菜','Ta Ke Cai'),(462,'油菜','Rape'),(463,'不結球白菜','Cabbage Without Heads'),(464,'芥菜','Mustard'),(465,'結球白菜','Heading Cabbage'),(466,'黑種草','Nigella Sativa'),(467,'觀賞玉米','Ornamental Corn'),(468,'古代稀','Rare In Ancient Times'),(469,'貝殼花','Shell Flower'),(470,'洋桔梗','Lisianthus'),(471,'羽衣甘藍','Kale'),(472,'芥藍','Kale'),(473,'其他稻米','Other Rice'),(474,'秈糯','Indica'),(475,'稉糯','Japonica'),(476,'軟秈','Soft Indica'),(477,'硬秈','Hard Indica'),(478,'稉稻','Japonica Rice'),(479,'觀賞南瓜','Ornamental Pumpkins'),(480,'松蟲草','Cordyceps Sinensis'),(481,'風鈴花','Campanula'),(482,'紫羅蘭','Violet'),(483,'葉牡丹','Leaf Peony'),(484,'百日草','Zinnia'),(485,'鱗托菊','Chrysanthemum'),(486,'瓜葉菊','Cineraria'),(487,'向日葵','Sunflower'),(488,'矢車菊','Cornflower'),(489,'雲南菊','Yunnan Chrysanthemum'),(490,'金盞花','Marigold'),(491,'千日紅','Qianrihong'),(492,'藜','Quinoa'),(493,'雞冠花','Cockscomb'),(494,'紅莧菜','Red Amaranth'),(495,'雁來紅','Yanlaihong'),(496,'萬代蘭','Vanda Orchid'),(497,'腎藥蘭','Kidney Orchid'),(498,'皇后蘭','Queen Orchid'),(499,'樹攔','Tree Barrier'),(500,'蜘蛛蘭','Spider Orchid'),(501,'千代蘭','Chiyolan'),(502,'其他果樹','Other Fruit Trees'),(503,'可可','Cocoa'),(504,'胡桃','Walnut'),(505,'蘋婆','Ping Po'),(506,'長山核桃','Long Pecan'),(507,'澳洲胡桃','Australian Walnut'),(508,'栗子','Chestnut'),(509,'胡榛子','Hu Zhenzi'),(510,'腰果','Cashew'),(511,'扁桃','Almond'),(512,'杏仁','Almond'),(513,'檳榔','Betel Nut'),(514,'椰子','Coconut'),(515,'其它核果','Other Stone Fruits'),(516,'棗椰子','Date Palm'),(517,'爪哇橄欖','Javanese Olives'),(518,'橄欖','Olives'),(519,'錫蘭橄欖','Ceylon Olives'),(520,'印度棗','Indian Dates'),(521,'中國棗','Chinese Dates'),(522,'酪梨','Avocado'),(523,'梅','Plum'),(524,'杏','Apricot'),(525,'櫻桃','Cherry'),(526,'李','Plum'),(527,'桃','Peach'),(528,'油柑','Tangerine'),(529,'紅毛丹','Rambutan'),(530,'龍眼','Longan'),(531,'荔枝','Litchi'),(532,'其他仁果','Other Pome Fruits'),(533,'枇杷','Loquat'),(534,'梨','Pear'),(535,'蘋果','Apple'),(536,'其他漿果','Other Berries'),(537,'木鱉果','Wood Turtle Fruit'),(538,'山竹','Mangosteen'),(539,'榴槤','Durian'),(540,'西印度櫻桃','Acerola Cherry'),(541,'人心果','Sapodilla'),(542,'神秘果','Miracle Fruit'),(543,'黃金果','Golden Fruit'),(544,'蛋黃果','Egg Yolk Fruit'),(545,'石榴','Pomegranate'),(546,'楊梅','Bayberry'),(547,'榴槤蜜','Durian Honey'),(548,'桑椹','Mulberry'),(549,'小波羅蜜','Little Jackfruit'),(550,'波羅蜜','Jackfruit'),(551,'無花果','Fig'),(552,'麵包果','Breadfruit'),(553,'柿','Persimmon'),(554,'羅望子','Tamarind'),(555,'釋迦','Shakya'),(556,'藍莓','Blueberry'),(557,'奇異果','Kiwi'),(558,'百香果','Passion Fruit'),(559,'楊桃','Carambola'),(560,'葡萄','Grape'),(561,'嘉寶果','Jiabao Fruit'),(562,'蓮霧','Wax Apple'),(563,'番石榴','Guava'),(564,'鳳梨','Pineapple'),(565,'芭蕉','Banana'),(566,'香蕉','Banana'),(567,'番木瓜','Papaya'),(568,'其他柑橘','Other Citrus'),(569,'金柑與小果柑橘','Kumquats And Tangerines'),(570,'枸櫞','Citron'),(571,'甜橙','Sweet Orange'),(572,'寬皮柑','Kuanpi Mandarin Orange'),(573,'葡萄柚','Grapefruit'),(574,'柚子','Grapefruit'),(575,'其他蔬菜','Other Vegetables'),(576,'其他長期蔬菜','Other Long Term Vegetables'),(577,'其他短期蔬菜','Other Short-Term Vegetables'),(578,'採種用蔬菜','Vegetables For Planting'),(579,'小海帶','Small Kelp'),(580,'髮菜','Nostoc'),(581,'海菜','Seaweed'),(582,'海帶','Kelp'),(583,'其他菇類','Other Mushrooms'),(584,'松茸','Matsutake'),(585,'紫丁香蘑','Lilac Mushroom'),(586,'金福菇','Golden Mushroom'),(587,'白玉菇','White Jade Mushroom'),(588,'鴻喜菇','Hongxi Mushroom'),(589,'酒杯菇','Wine Glass Mushroom'),(590,'白木耳','White Fungus'),(591,'金耳','Golden Ear'),(592,'滑菇','Mushroom'),(593,'草菇','Straw Mushroom'),(594,'粉紅玫瑰菇','Pink Rose Mushroom'),(595,'蠔菇','Oyster Mushrooms'),(596,'秀珍菇','Xiuzhen Mushroom'),(597,'白靈菇','White Mushroom'),(598,'杏鮑菇','King Oyster Mushroom'),(599,'鮑魚菇','Abalone Mushroom'),(600,'珊瑚菇','Coral Mushroom'),(601,'竹蓀','Bamboo Fungus'),(602,'舞菇','Maitake Mushrooms'),(603,'香菇','Mushroom'),(604,'金針菇','Flammulina Enoki'),(605,'猴頭菇','Hericium'),(606,'靈芝','Ganoderma Lucidum'),(607,'北蟲草','Cordyceps Militaris'),(608,'牛肝菌','Boletus'),(609,'茶樹菇','Tea Tree Mushroom'),(610,'毛木耳','Fungus'),(611,'斤耳','Jin Er'),(612,'黑木耳','Black Fungus'),(613,'雞肉絲菇','Chicken Shredded Mushrooms'),(614,'雞腿菇','Coprinus Comatus'),(615,'巴西蘑菇',NULL),(616,'洋菇','Mushrooms'),(617,'其他芽菜','Other Sprouts'),(618,'綠豆芽','Mung Bean Sprouts'),(619,'紅豆芽','Red Bean Sprouts'),(620,'蠶豆芽','Broad Bean Sprouts'),(621,'苜蓿芽','Alfalfa Sprouts'),(622,'黑豆芽','Black Bean Sprouts'),(623,'黃豆芽','Soybean Sprouts'),(624,'蕎麥芽菜','Buckwheat Sprouts'),(625,'落花生芽菜','Groundnut Sprouts'),(626,'蘿蔔芽菜','Radish Sprouts'),(627,'青花菜芽菜','Broccoli Sprouts'),(628,'芥藍芽菜','Kale Sprouts'),(629,'甘藍芽菜','Kale Sprouts'),(630,'其他果菜苗','Other Fruit And Vegetable Seedlings'),(631,'其他果菜','Other Fruits And Vegetables'),(632,'草莓','Strawberry'),(633,'黃秋葵','Okra'),(634,'菱角','Water Chestnut'),(635,'破布子','Rags'),(636,'香瓜茄','Cantaloupe And Eggplant'),(637,'茄子','Eggplant'),(638,'小果番茄','Small Fruit Tomatoes'),(639,'番茄','Tomato'),(640,'其他瓜菜','Other Vegetables'),(641,'蛇瓜','Snake Melon'),(642,'隼人瓜','Hayato Melon'),(643,'越瓜','Viet Melon'),(644,'苦瓜','Momordica Charantia'),(645,'胡瓜','Cucumber'),(646,'絲瓜','Loofah'),(647,'扁蒲','Bianpu'),(648,'南瓜','Pumpkin'),(649,'冬瓜','Winter Melon'),(650,'小菊','Xiaoju'),(651,'紫菀','Aster'),(652,'紐西蘭麻','New Zealand Hemp'),(653,'火炬百合','Torch Lily'),(654,'萱草','Hemerocallis'),(655,'狐尾百合','Foxtail Lily'),(656,'假葉樹','Artificial Tree'),(657,'鳴子百合','Naruko Lily'),(658,'天鵝絨','Velvet'),(659,'伯利恆之星','Star Of Bethlehem'),(660,'風信子','Hyacinth'),(661,'吊蘭','Chlorophytum'),(662,'葉蘭','Ye Lan'),(663,'文竹','Asparagus'),(664,'蘆筍草','Asparagus Grass'),(665,'武竹','Wu Zhu'),(666,'夜來香','Tuberose'),(667,'翠珠花','Emerald Flower'),(668,'海芋','Alocasia'),(669,'合果芋','Yam'),(670,'白鶴芋','Spathiphyllum'),(671,'黛粉葉','Daifen Leaves'),(672,'觀音蓮','Avalokitesvara'),(673,'唐棉','Tang Mian'),(674,'紫嬌花','Purple Jiaohua'),(675,'火球花','Fireball Flower'),(676,'孤挺花','Amaryllis'),(677,'文殊蘭','Manjushri'),(678,'繡球蔥','Hydrangea Onion'),(679,'百子蓮','Agapanthus'),(680,'水仙','Narcissus'),(681,'石蒜','Lycoris'),(682,'君子蘭','Clivia'),(683,'水仙百合','Narcissus Lily'),(684,'菖蒲','Calamus'),(685,'其他木本花卉','Other Woody Flowers'),(686,'山茶花','Camellia'),(687,'木羊齒','Wood Fern'),(688,'柳','Willow'),(689,'七里香','Qilixiang'),(690,'六月雪','Snow In June'),(691,'仙丹花','Elixir'),(692,'梔子花','Gardenia'),(693,'寒丁子','Handingzi'),(694,'麻葉繡球','Hemp Leaf Hydrangea'),(695,'海神花','Poseidon Flower'),(696,'針墊花','Pincushion Flower'),(697,'雪松','Cedar'),(698,'新西蘭','New Zealand'),(699,'林投','Lin Tou'),(700,'牡丹','Peony'),(701,'女貞','Privet'),(702,'茉莉','Jasmine'),(703,'素馨','Jasmine'),(704,'連翹','Forsythia'),(705,'尤加利','Eucalyptus'),(706,'蠟梅','Wintersweet'),(707,'降天桑','Falling Into Heaven'),(708,'香樹蘭','Fragrant Tree Orchid'),(709,'洛神葵','Roselle'),(710,'玉蘭花','Magnolia'),(711,'金絲桃','Hypericum'),(712,'金雀花','Broom'),(713,'三角尤加利','Triangle Eucalyptus'),(714,'聖誕紅','Christmas Red'),(715,'羽毛花','Feather Flower'),(716,'變葉木','Changeleaf Wood'),(717,'蘇鐵','Cycad'),(718,'側柏','Arborvitae'),(719,'香冠柏','Cedar'),(720,'柳杉','Cryptomeria'),(721,'扁柏','Hinoki Cypress'),(722,'征木','Zheng Mu'),(723,'五彩千年木','Colorful Thousand-Year-Old Wood'),(724,'星點木','Star Point Wood'),(725,'青竹','Green Bamboo'),(726,'百合竹','Lily Bamboo'),(727,'虎斑木','Tabby Wood'),(728,'朱蕉','Zhu Jiao'),(729,'觀音棕竹','Guanyin Palm Bamboo'),(730,'黃椰子','Yellow Coconut'),(731,'八角金盤','Octagon Gold Plate'),(732,'藍星花','Blue Star Flower'),(733,'其他一二年生草本','Other Perennial Herbs'),(734,'紅茄','Red Eggplant'),(735,'蚌蘭','Mussel Orchid'),(736,'宮燈百合','Palace Lantern Lily'),(737,'嘉蘭','Gloria'),(738,'滿天星','Gypsophila'),(739,'深山櫻','Mountain Cherry'),(740,'康乃馨','Carnation'),(741,'夕霧花','Evening Mist Flower'),(742,'三角桔梗','Triangular Platycodon'),(743,'美人蕉','Canna'),(744,'擎天鳳梨','Qingtian Pineapple'),(745,'觀果鳳梨','Guanguo Pineapple'),(746,'蜻蜓鳳梨','Dragonfly Pineapple'),(747,'麥桿菊','Strawberry'),(748,'琉璃菊','Liuliju'),(749,'一枝黃花','Goldenrod'),(750,'澳洲鼓槌菊','Australian Drumstick Daisy'),(751,'麟麟菊','Linlinju'),(752,'非洲菊','Gerbera'),(753,'白藍菊','White Blue Chrysanthemum'),(754,'大理花','Dahlia'),(755,'波斯菊','Cosmos'),(756,'麵線菊','Chrysanthemum Noodle'),(757,'大菊','Daju'),(758,'射干','Cumshot'),(759,'鳶尾','Iris'),(760,'小蒼蘭','Freesia'),(761,'段菊','Duan Ju'),(762,'繡球花','Hydrangeas'),(763,'赫蕉','He Jiao'),(764,'袋鼠花','Kangaroo Flower'),(765,'龍膽','Gentian'),(766,'羽扇豆','Lupine'),(767,'金翠花','Golden Cuihua'),(768,'八卦草','Baguacao'),(769,'初雪草','Chuxucao'),(770,'水莞','Shui Wan'),(771,'巨果薑','Ginger'),(772,'水晶花','Crystal Flower'),(773,'補雪草','Centella'),(774,'卡斯比亞','Casbia'),(775,'虎尾花','Tigertail Flower'),(776,'睡蓮','Water Lily'),(777,'竹芋','Arrowroot'),(778,'鬱金香','Tulip'),(779,'波羅門蔘','Balsamic Ginseng'),(780,'牛蒡','Burdock'),(781,'其他堅果','Other Nuts'),(782,'雲芝','Yunzhi'),(783,'其他豆菜','Other Bean Dishes'),(784,'龍鬚菜','Asparagus'),(785,'食用薊','Edible Thistle'),(802,'皇帝豆','Emperor Beans'),(803,'包心白菜','Cabbage'),(804,'青江白菜','Qingjiang Cabbage'),(805,'敏豆','Min Dou'),(806,'小黃瓜','Gherkin'),(807,'旱芹','Celery'),(808,'粉豆','Pink Beans'),(809,'桑果','Mulberry'),(810,'洋香瓜','Cantaloupe'),(811,'柑桔','Citrus'),(812,'柿子','Persimmon'),(813,'文旦','Wendan'),(814,'樹葡萄','Tree Grape'),(815,'牛奶果','Milk Fruit'),(816,'草花','Grass Flower'),(817,'球根花卉','Flower Bulbs'),(818,'蘭類','Orchids'),(819,'觀葉植物','Foliage Plants'),(820,'香花植物','Fragrant Flower Plant'),(821,'觀賞樹木','Ornamental Trees'),(822,'菊科','Asteraceae'),(823,'薑科','Zingiberaceae'),(824,'荖籐','Vine'),(825,'烏心石','Black Heart Stone'),(826,'茉草','Jasmine'),(827,'水稻','Rice'),(828,'肖楠','Xiao Nan'),(829,'大葉楠','Dayenan'),(830,'冬蟲夏草','Cordyceps Sinensis'),(831,'水黃皮','Watery Yellow Skin'),(832,'草皮','Turf'),(833,'牛樟','Niu Zhang'),(834,'雜草','Weeds'),(835,'菊苣','Endive'),(836,'蘿勒','Basil'),(837,'黑松','Lodgepole Pine'),(838,'檜木','Hinoki'),(839,'柳樹','Willow'),(840,'蘋婆果','Apple Fruit');
/*!40000 ALTER TABLE `crop` ENABLE KEYS */;

--
-- Table structure for table `disease`
--

DROP TABLE IF EXISTS `disease`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `disease` (
  `disease_id` int NOT NULL AUTO_INCREMENT,
  `crop_id` int DEFAULT NULL,
  `disease_name` varchar(100) NOT NULL,
  `description` text NOT NULL,
  `treatment` varchar(100) NOT NULL,
  PRIMARY KEY (`disease_id`),
  KEY `disease_ibfk_1` (`crop_id`),
  CONSTRAINT `disease_ibfk_1` FOREIGN KEY (`crop_id`) REFERENCES `crop` (`crop_id`)
) ENGINE=InnoDB AUTO_INCREMENT=22 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `disease`
--

/*!40000 ALTER TABLE `disease` DISABLE KEYS */;
INSERT INTO `disease` VALUES (1,NULL,'土壤呈強酸性','根生長不良、生長延遲。','施用石灰或草木灰中和酸性，增加土壤 pH 值。'),(2,NULL,'土壤通氣不良','根部腐爛。','中耕鬆土，或在介質中加入珍珠石、增加孔隙。'),(3,NULL,'土壤排水不良','常因底層有硬土層造成生長延遲。','改善排水系統，打破深層硬土，或更換疏水性好的介質。'),(4,NULL,'土壤過份乾燥','葉尖捲曲褐化，出現斑點或斑塊，全株黃化、落葉、萎凋或大量落葉。','建立規律澆水制度，可覆蓋稻草減少水分蒸發。'),(5,NULL,'土壤酸鹼值不平衡','嫩葉退綠造成葉片呈黃綠狀。','檢測土壤 pH 值，根據結果調整（酸則加鹼，鹼則加酸）。'),(6,NULL,'土壤鹽基(EC)過高','葉尖捲曲褐化，落葉、萎凋或大量落葉。','以大量清水淋洗土壤排除鹽分，並暫停施肥。'),(7,NULL,'土壤條件環境劇變','根系發育不良、植株衰弱。','設置遮陽網或溫室控溫，避免環境因子短時間內大幅震盪。'),(8,NULL,'微量元素不平衡','嫩葉退綠造成葉片呈黃綠狀。','噴施綜合微量元素葉面肥，快速補充缺失養分。'),(9,NULL,'肥料中之鹽分累積','土壤表層有結晶體、堅硬。','移除表土結晶，充分灌水洗鹽，減少化學肥料使用。'),(10,NULL,'氮肥過多','頂端葉片繁茂但開花少。','減少氮肥，增施磷鉀肥，促進花芽分化。'),(11,NULL,'肥料傷害(肥料過多)','葉尖褐化或出現塊斑、葉片黃化，嚴重者葉片乾縮、落葉，甚至全株萎凋。','立即大量澆水稀釋肥料濃度，嚴重時需更換部分土壤。'),(12,NULL,'肥料不足','葉片黃化、生長延遲、葉片減少及植株短小。','定期定量施用平衡型肥料 (N-P-K 比例均衡)。'),(13,NULL,'肥料不足且氮肥嚴重不足','植株矮化、新葉變小、老葉黃化。','追施速效性氮肥（如尿素），並注意土壤有機質補充。'),(14,NULL,'缺鉀','葉片由老葉葉緣向內黃化。','施用硫酸鉀或硝酸鉀肥料，增強植株抗性。'),(15,NULL,'缺鎂','老葉葉脈間黃化，新葉黃化但葉脈仍為綠色。','施用苦土石灰（含有碳酸鎂）或噴灑硫酸鎂溶液。'),(16,NULL,'水分不足','葉片黃化、頂端葉片褐化、植株萎凋。','立即補水，並確保水分滲透至根系所在深度。'),(17,NULL,'水分過多','老葉黃化，葉間捲曲褐化，葉尖褐化或由葉尖開始出現黃色、褐色斑點，葉片減少，嚴重者落葉；生長不良、生長延遲、植株褪色，嚴重者莖部腐爛、植株萎凋。','停止澆水，加強通風，若已腐爛需剪除爛根並換盆消毒。'),(18,NULL,'濕度太低','頂端葉片褐化、葉片乾縮。','在植株周圍噴霧增加空氣濕度，或使用加濕器。'),(19,NULL,'乾旱','葉片黃化，葉片出現黃色、褐色斑點。','穩定灌溉，並考慮在土表鋪設覆蓋物保持濕潤。'),(20,NULL,'冬季光照不足','生長延遲。','移動植株至向陽處，或使用人工植物燈補光。'),(21,NULL,'白粉病','葉面出現白色粉狀斑點，為白粉病感染。','改善通風、移除病葉，可噴灑硫磺或苦楝油防治。');
/*!40000 ALTER TABLE `disease` ENABLE KEYS */;

--
-- Table structure for table `pests`
--

DROP TABLE IF EXISTS `pests`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `pests` (
  `pest_id` int NOT NULL AUTO_INCREMENT,
  `crop_id` int NOT NULL,
  `pest_name` varchar(100) NOT NULL,
  `description` text NOT NULL,
  `treatment` varchar(100) NOT NULL,
  PRIMARY KEY (`pest_id`),
  KEY `crop_id` (`crop_id`),
  CONSTRAINT `pests_ibfk_1` FOREIGN KEY (`crop_id`) REFERENCES `crop` (`crop_id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `pests`
--

/*!40000 ALTER TABLE `pests` DISABLE KEYS */;
INSERT INTO `pests` VALUES (1,2,'蟲害','葉片出現明顯孔洞與邊緣褐化，疑遭蟲害。','仔細檢查葉背及土壤，手動移除害蟲或使用天然驅蟲劑。'),(2,2,'薊馬','葉面有微小白斑點，可能為初期刺吸式害蟲。','密切觀察，若蟲害加劇可考慮使用生物防治或苦楝油。');
/*!40000 ALTER TABLE `pests` ENABLE KEYS */;

--
-- Table structure for table `plant_diary`
--

DROP TABLE IF EXISTS `plant_diary`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `plant_diary` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `crop_id` int NOT NULL,
  `status_name` varchar(100) DEFAULT NULL,
  `image_url` varchar(2048) NOT NULL,
  `disease_id` int DEFAULT NULL,
  `pest_id` int DEFAULT NULL,
  `confidence` float NOT NULL,
  `suggestion` text NOT NULL,
  `treatment` text,
  `user_note` text,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=21 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `plant_diary`
--

/*!40000 ALTER TABLE `plant_diary` DISABLE KEYS */;
INSERT INTO `plant_diary` VALUES (1,1,2,'蚜蟲','C:\\Users\\User\\OneDrive\\Desktop\\MyProject\\dataset\\lettuce_pointed\\disease\\IMG_14_aug.albumentations1_aug.albumentations2.jpg',NULL,NULL,0.8,'葉片上出現小型深色害蟲，可能是蚜蟲，吸食汁液。',NULL,'hi','2026-03-14 15:56:26'),(2,1,409,'白粉病','C:\\Users\\User\\OneDrive\\Desktop\\MyProject\\dataset\\chives_disease\\IMG_1420_404 (2).jpg',1,NULL,0.88,'葉片出現白色粉狀黴斑。',NULL,'hi','2026-03-14 15:57:20'),(3,1,432,'Healthy','C:\\Users\\User\\OneDrive\\Desktop\\MyProject\\dataset\\chives_healthy\\IMG_1423_273.jpg',NULL,NULL,0.9,'此植物外觀健康，無明顯病蟲害跡象。',NULL,'hi','2026-03-14 16:04:11'),(4,1,2,'Healthy','C:\\Users\\User\\OneDrive\\Desktop\\MyProject\\dataset\\lettuce_fushan\\disease\\IMG_15_aug.bright.jpg',NULL,NULL,0.95,'植株生長良好，葉片翠綠。',NULL,'hi','2026-03-14 16:05:24'),(5,1,2,'Anthracnose','C:\\Users\\User\\OneDrive\\Desktop\\MyProject\\dataset\\lettuce_fushan\\disease\\IMG_1330_aug.flip.jpg',4,NULL,0.85,'葉片出現深褐色凹陷壞死斑，中央穿孔。',NULL,'hi','2026-03-14 16:08:25'),(6,1,2,'炭疽病','C:\\Users\\User\\OneDrive\\Desktop\\MyProject\\dataset\\lettuce_fushan\\disease\\IMG_1330_aug.flip.jpg',NULL,NULL,0.92,'葉片出現深色不規則斑點，中心組織壞死腐爛。',NULL,'hi','2026-03-14 16:11:21'),(7,1,2,'炭疽病','C:\\Users\\User\\OneDrive\\Desktop\\MyProject\\dataset\\lettuce_fushan\\disease\\IMG_1330_aug.flip.jpg',5,NULL,0.88,'葉片出現褐色不規則病斑，中心可能破裂，顯示受炭疽病感染。',NULL,'hi','2026-03-14 16:16:23'),(8,1,2,'蟲害','C:\\Users\\User\\OneDrive\\Desktop\\MyProject\\dataset\\lettuce_fushan\\disease\\IMG_1288_aug.bright_aug.albumentations1.jpg',NULL,1,0.85,'葉片出現明顯孔洞與邊緣褐化，疑遭蟲害。',NULL,'hi','2026-03-16 15:35:25'),(9,1,2,'Healthy','static/uploads\\2a4d9f4f-62ce-48db-b545-5138cf45567a.jpg',NULL,NULL,0.95,'植株生長良好，葉片呈現健康翠綠。',NULL,'這個蔬菜好可愛','2026-03-17 16:17:31'),(10,1,648,'白粉病','static/uploads\\8dce3f18-0422-4a93-99db-c2a22c1aebf5.jpg',6,NULL,0.95,'葉片上出現白色粉狀物，這是由真菌引起的白粉病。',NULL,'你好嗎','2026-03-18 16:14:40'),(11,1,648,'白粉病','static/uploads\\8dce3f18-0422-4a93-99db-c2a22c1aebf5.jpg',6,NULL,0.95,'葉片上出現白色粉狀物，這是由真菌引起的白粉病。',NULL,'你好嗎','2026-03-18 16:14:40'),(12,1,2,'薊馬','static/uploads\\24e15811-cd5c-4184-b180-fcd48b618200.jpg',NULL,2,0.75,'葉面有微小白斑點，可能為初期刺吸式害蟲。',NULL,'西巴如馬','2026-03-18 16:19:15'),(13,1,2,'薊馬','static/uploads\\24e15811-cd5c-4184-b180-fcd48b618200.jpg',NULL,2,0.75,'葉面有微小白斑點，可能為初期刺吸式害蟲。',NULL,'西巴如馬','2026-03-18 16:19:15'),(14,1,2,'葉斑病','static/uploads\\f3ecc7c7-fe72-4fed-a1e8-0899befafba5.jpg',7,NULL,0.85,'葉面出現散佈的黑斑點，疑似葉斑病初步感染。',NULL,'西巴','2026-03-18 16:32:07'),(15,1,2,'Healthy','static/uploads/7b7ad086-a6d9-48a9-964b-e20d48c80c68.jpg',NULL,NULL,0.9,'葉片翠綠，結構完整，無明顯病蟲害，生長狀況良好。',NULL,'132','2026-03-23 17:37:16'),(18,2,2,'Healthy','static/uploads/IMG_1291_aug.albumentations_aug.albumentations2.jpg',NULL,NULL,0.99,'植物目前看起來很健康，狀況良好。',NULL,'258','2026-04-06 17:23:33'),(19,2,2,'缺鎂','static/uploads/IMG_1274.jpg',15,NULL,0.85,'葉片葉脈間黃化，葉緣褐化，可能是缺鎂。',NULL,'123654','2026-04-08 07:24:05'),(20,2,2,'Healthy','static\\uploads\\IMG_1331.jpg',NULL,NULL,0.95,'此植物生長狀況良好，葉片翠綠飽滿，沒有病蟲害跡象。','請繼續保持目前的良好管理，定期檢查，確保適當的水分和養分供應。','259','2026-04-10 16:33:02');
/*!40000 ALTER TABLE `plant_diary` ENABLE KEYS */;

--
-- Table structure for table `user`
--

DROP TABLE IF EXISTS `user`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user` (
  `user_id` int NOT NULL AUTO_INCREMENT,
  `username` varchar(50) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `email` varchar(100) DEFAULT NULL,
  `full_name` varchar(50) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `role` varchar(20) DEFAULT 'user',
  PRIMARY KEY (`user_id`),
  UNIQUE KEY `username` (`username`),
  UNIQUE KEY `email` (`email`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `user`
--

/*!40000 ALTER TABLE `user` DISABLE KEYS */;
INSERT INTO `user` VALUES (1,'admin','$2b$12$528HuluM6KgL6S/fjnew8eDvb9.1JfADvx0fdQelMvV3TtVkvx/N.','admin@example.com','admin','2026-04-09 15:19:47','admin'),(2,'123','$2b$12$54LMrXH8DXUTRxeyWV.x4.mF6SeIE8EJcud4cOKb/p8zc5qhUYY96','123@example.com','123','2026-04-06 15:35:25','user'),(3,'thomas','$2b$12$YJwymCA.a4T5iGp9ALEF1OPoHILzL1MTyt9/aZ9WLzUWUZpb4yw.O','123456@gmail.com','thomas','2026-04-03 15:50:49','user');
/*!40000 ALTER TABLE `user` ENABLE KEYS */;

--
-- Dumping routines for database 'plant_db'
--
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-04-11  0:37:54
