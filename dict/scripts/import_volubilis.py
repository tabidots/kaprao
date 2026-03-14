from dict.scripts.paths import DB_PATH, RAW_DIR
from dict.scripts.phonetic_utils import romanize_from_volubilis, make_plain
from pythainlp.corpus import get_corpus
from itertools import zip_longest
import csv
import json
import re
import sqlite3

RAW_DATA_PATH = RAW_DIR / "VOLUBILIS Mundo(Volubilis).csv"

DATA_FIXES = {
    # VPHON
    "_neung _meūn ; _meūn ; _meūn _neung": "_neung _meūn = _meūn",
    "_neung -phan ; -phan ; -phan _neung": "_neung -phan = -phan",
    "_neung /saēn ; /saēn ; /saēn _neung": "_neung /saēn = /saēn",
    "_neung ¯lān ; ¯lān ; ¯lān _neung": "_neung ¯lān = ¯lān",
    "_neung ¯røi ; ¯røi ; ¯røi _neung": "_neung ¯røi = ¯røi",
    "_øk _kī -mōng ; … _øk _kī -mōng": "_øk _kī -mộng (… _øk _kī -mộng)",
    "_sat_bu_rut ; _sat_ta_bu_rut": "_sat_bu_rut = _sat_ta_bu_rut",
    "_sōk ; _sōk_ka": "_sōk = _sōk_ka",
    "-phē_sat¯cha ; -phē_sat": "-phē_sat¯cha = -phē_sat",
    "-plā _ka-phong -daēng ; [-plā _kra-phong -daēng]": "-plā _ka-phong -daēng",
    "-plā _ka-phong /khāo ; [-plā _kra-phong /khāo]": "-plā _ka-phong /khāo",
    "¯kha_ti _a-nā¯thip_pa-tai": "¯kha_ti _a-nā¯thip_pa-tai = ¯kha_ti _a-nā¯thi_pa-tai",
    "¯ma/hā_ka_sa-tri": "¯ma/hā_ka_sat",
    "¯røi _et ; _neung ¯røi _et ; _neung ¯røi _neung": "¯røi _et = _neung ¯røi _et",
    "ākīen": "-ā-kīen",
    "chothannasala": "_chōt/khlāo",
    r"_ka\bang-lom ; [_kra\bang-lom]": r"_ka\bang-lom",
    r"_Ut¯tha-yān_haeng\chāt -Phū /Hin Rǿng \Klā": r"_Ut¯tha-yān_haeng\chāt -Phū /Hin \Rǿng \Klā",
    r"\khī ; \khī-": r"\khī-",
    r"¯røi \kāo_sip \kāo ; ¯røi \kāo\kāo": r"¯røi \kāo_sip \kāo",
    r"/Lūang \Phø \Thūat (_yīep ¯nām ¯tha-lē _jeūt)": r"/Lūang \Phø \Thūat _yīep ¯nām ¯tha-lē _jeūt",
    r"(/Sam¯nak-ngān ¯Kha¯na-kam¯ma-kān \Khā\rāt¯cha-kān -Phon¯la-reūoen)": r"Kø.Phø. (/Sam¯nak-ngān ¯Kha¯na-kam¯ma-kān \Khā\rāt¯cha-kān -Phon¯la-reūoen)",
    r"(-Krom _Ut/sā_ha-kam ¯Pheūn/thān ¯lae -Kān /Meūang\raē)": r"Køphørø. (-Krom _Ut/sā_ha-kam ¯Pheūn/thān ¯lae -Kān /Meūang\raē)",
    r"(/Sam¯nak-ngān ¯Kha¯na-kam¯ma-kān ¯phat¯tha-nā ¯Ra_bop \Rāt ¯cha-kān)": r"Kø.Phø.Rø. (/Sam¯nak-ngān ¯Kha¯na-kam¯ma-kān ¯phat¯tha-nā ¯Ra_bop \Rāt ¯cha-kān)",
    r"¯Kha¯na-kam¯Ma-kān _Sit¯thi ¯ma¯nut_sa¯ya-chon _haeng \Chāt": r"¯Kha¯na-kam¯ma-kān _Sit¯thi ¯Ma¯nut_sa¯ya-chon _haeng \Chāt",
    r"(¯Kha¯na-kam¯Ma-kān _Sit¯thi ¯ma¯nut_sa¯ya-chon _haeng \Chāt)": r"Køsømø. (¯Kha¯na-kam¯ma-kān _Sit¯thi ¯Ma¯nut_sa¯ya-chon _haeng \Chāt)",
    "_nǿi ¯si (... _nǿi ¯si)": "_nǿi ¯si",
    r"\thī/nai (... \thī/nai)": r"\thī/nai",
    "_øk _kī -mōng ; … _øk _kī -mōng": "_øk _kī -mộng",
    "-thē¯wa-nā¯kha-rī  (= -thē¯wa-nā-khrī)": "-thē¯wa-nā-kha-rī",
    "(_Kra-thing -Daēng)": r"\Ret Būl ; -Kra-thing -Daēng",
    "¯Na-rā ¯thi\wāt": r"¯Na-rā¯thi\wāt",
    r"-Jang_wat ¯Na-rā ¯thi\wāt": r"-Jang_wat ¯Na-rā¯thi\wāt",
    r"-Meūang ¯Na-rā ¯thi\wāt": r"-Meūang ¯Na-rā¯thi\wāt",
    r"-Am-phoē -Meūang ¯Na-rā ¯thi\wāt": r"-Am-phoē -Meūang ¯Na-rā¯thi\wāt",
    r"_Sa/nām-bin ¯Na-rā ¯thi\wāt": r"_Sa/nām-bin ¯Na-rā¯thi\wāt",
    r"\Thā-ā_kāt_sa-yān ¯Na-rā ¯thi\wāt": r"\Thā-ā_kāt_sa-yān ¯Na-rā¯thi\wāt",
    "-pā_tha-": "-pā_tha",
    r"-nā-nā \chāt": r"-nā-nā\chāt",
    
    # THAI
    
    "กกต. (คณะกรรมการการเลือกตั้ง) ; กกต. (คณะกรรมการเลือกตั้ง)": "กกต. (คณะกรรมการการเลือกตั้ง)",
    "สาธารณรัฐมาซิโดเนีย": "สาธารณรัฐมาซิโดเนียเหนือ",
    "กล้ามเนื้อเอก็เทนเซอร์": "กล้ามเนื้อเอกซ์เทนเซอร์",
    "ประเทศมาซิโดเนีย": "ประเทศมาซิโดเนียเหนือ",
    "น่า- ; น่า-": "น่า-",
    "ปปลาแอนโชวี่": "ปลาแอนโชวี่",
    "ศูนย์โควิด มท.": "ศูนย์โควิด",
    "-จารย์)": "จารย์ (-จารย์)",
    "… เถิด": "เถิด (-เถิด)",
    "-การ": "การ (-การ)",
    "กุกกุร": "กุกกุร-",
    "โจร": "โจร-",
    "สหัส": "สหัส-",
    "เกงเขง , เกงเคง": "เกงเขง ; เกงเคง",
    "ปรีดิยาธร เทวกุล ; ม.ร.ว. ปรีดิยาธร เทวกุล": "ปรีดิยาธร เทวกุล ; หม่อมราชวงศ์ปรีดิยาธร เทวกุล",
    "ราไวย์": "หาดราไวย์",
    "เสก โลโซ (เสกสรรค์ ศุขพิมาย)": "เสกสรรค์ ศุขพิมาย (เสก โลโซ)",
    "หมาจิ้งจอกเฟนเนก": "สุนัขจิ้งจอกเฟนเนก",
    "ราชานุภาพ": "ดำรง ราชานุภาพ",
    "ห้าแยกชิบูย่า": "ห้าแยกชิบูย่า ; แยกชิบูย่า",
    "ผู้ที่ลอบวางเพลิง ; ผู้ที่ลอบวางเพลิง": "ผู้ที่ลอบวางเพลิง ; ผู้ลอบวางเพลิง",
    "บาเยิร์น มิวนิก บาเยิร์น มิวนิค ; บาเยิร์น": "บาเยิร์น มิวนิก = บาเยิร์น มิวนิค ; บาเยิร์น",
    "สุรชัย ด่านวัฒนานุสรณ = สุรชัย แซ่ด่าน": "สุรชัย ด่านวัฒนานุสรณ ; สุรชัย แซ่ด่าน",
    "มักเขียนผิดเป็นคำว่า “ ...”": "มักเขียนผิดเป็นคำว่า",
    "เมล่อนเนื้อเขียว ; เมล่อนเนื้อเขียว": "เมล่อนเนื้อเขียว; เมล่อนเนื้อสีเขียว",
    "คริฤเก็ต": "คริกเกต",
    "มลรัฐลุยเซียนา": "รัฐลุยเซียนา",
    "มลรัฐแคลิฟอร์เนีย": "รัฐแคลิฟอร์เนีย",
    "อาริสโตเติล = อริสโตเติล": "อาริสโตเติล ; อริสโตเติล",
    "กฎมนเทียรบาล ; กฎมณเทียรบาล": "กฎมนเทียรบาล = กฎมณเทียรบาล",
    "กตัตตากรรม ; กฏัตตากรรม": "กตัตตากรรม = กฏัตตากรรม",
    "กบเคอร์มิต ; กบเคอร์มิท": "กบเคอร์มิต = กบเคอร์มิท",
    "กปณก ; กปนก": "กปณก = กปนก",
    "กรมชลประทาน ; กรมชลฯ": "กรมชลประทาน = กรมชลฯ",
    "กรมอุทยานแห่งชาติ ; กรมอุทยานฯ": "กรมอุทยานแห่งชาติ = กรมอุทยานฯ",
    "กระบะลอย ; กะบะลอย": "กระบะลอย = กะบะลอย",
    "กระแหม็บ ; กระแหม็บ ๆ = กระแหม็บๆ ; [กระแหมบ]": "กระแหม็บ ; กระแหม็บ ๆ = กระแหม็บๆ",
    "กลาสโกว์ เซลติก": "กลาสโกว์ เซลติก ; เซลติก",
    "กะบังลม ; [กระบังลม]": "กะบังลม",
    "กัป ; [กัปป์]": "กัป",
    "กางเกงวอม ; กางเกงวอร์ม": "กางเกงวอม = กางเกงวอร์ม",
    "การพูดแบบเท็ด ; การพูดแบบ TED": "การพูดแบบเท็ด = การพูดแบบ TED",
    "การรถไฟแห่งประเทศไทย (รฟท.) ; รถไฟไทย ; การรถไฟฯ": "การรถไฟแห่งประเทศไทย = การรถไฟฯ (รฟท.) ; รถไฟไทย",
    "การุญ ; การุณย์": "การุญ = การุณย์",
    "เกจ์ ; เก": "เกจ์ = เก",
    "เกม ; เกมส์": "เกม = เกมส์",
    "เกรดเอ ; เกรด A": "เกรดเอ = เกรด A",
    "เกาสง ; เกาสฺยง": "เกาสง = เกาสฺยง",
    "โกฐจุฬาลัมพา ; โกฐจุฬาลำพา": "โกฐจุฬาลัมพา = โกฐจุฬาลำพา",
    "โกฐชฎามังษี ; โกฐชฎามังสี": "โกฐชฎามังษี = โกฐชฎามังสี",
    "ขนมปังสีขา": "ขนมปังสีขา ; ขนมปังขา",
    "ขัตติยะ สวัสดิผล ; พล.ต. ดร.ขัตติยะ สวัสดิผล (เสธ.แดง)": "ขัตติยะ สวัสดิผล = พล.ต. ดร.ขัตติยะ สวัสดิผล (เสธ.แดง)",
    "เขื่อนป่าสักชลสิทธิ์ ; เขื่อนป่าสักฯ": "เขื่อนป่าสักชลสิทธิ์ = เขื่อนป่าสักฯ",
    "แขม ; แขมร์": "แขม = แขมร์",
    "คลื่นลูกที่ 2 ; คลื่นลูกที่สอง": "คลื่นลูกที่ 2 = คลื่นลูกที่สอง",
    "คลื่นลูกที่ 3 ; คลื่นลูกที่สาม": "คลื่นลูกที่ 3 = คลื่นลูกที่สาม",
    "ความปลอดภัยทางการบิน": "ความปลอดภัยาทางการบิน ; ความปลอดภัยาการบิน",
    "คอมพ์ ; คอมฯ": "คอมพ์ = คอมฯ",
    "เคบายา เกอบายา": "เคบายา ; เกอบายา",
    "เครื่องหมาย At sign ; เครื่องหมาย แอดไซน์": "เครื่องหมาย แอดไซน์",
    "จังหวัดกระบี่ ; จ.กระบี่": "จังหวัดกระบี่ = จ.กระบี่",
    "จังหวัดกาญจนบุรี ; จ.กาญจนบุรี": "จังหวัดกาญจนบุรี = จ.กาญจนบุรี",
    "จังหวัดกาฬสินธุ์ ; จ.กาฬสินธุ์": "จังหวัดกาฬสินธุ์ = จ.กาฬสินธุ์",
    "จังหวัดกำแพงเพชร ; จ.กำแพงเพชร": "จังหวัดกำแพงเพชร = จ.กำแพงเพชร",
    "จังหวัดขอนแก่น ; จ.ขอนแก่น": "จังหวัดขอนแก่น = จ.ขอนแก่น",
    "จังหวัดจันทบุรี ; จ.จันทบุรี": "จังหวัดจันทบุรี = จ.จันทบุรี",
    "จังหวัดฉะเชิงเทรา ; จ.ฉะเชิงเทรา": "จังหวัดฉะเชิงเทรา = จ.ฉะเชิงเทรา",
    "จังหวัดชลบุรี ; จ.ชลบุรี": "จังหวัดชลบุรี = จ.ชลบุรี",
    "จังหวัดชัยนาท ; จ.ชัยนาท": "จังหวัดชัยนาท = จ.ชัยนาท",
    "จังหวัดชัยภูมิ ; จ.ชัยภูมิ": "จังหวัดชัยภูมิ = จ.ชัยภูมิ",
    "จังหวัดชุมพร ; จ.ชุมพร": "จังหวัดชุมพร = จ.ชุมพร",
    "จังหวัดเชียงราย ; จ.เชียงราย": "จังหวัดเชียงราย = จ.เชียงราย",
    "จังหวัดเชียงใหม่ ; จ.เชียงใหม่": "จังหวัดเชียงใหม่ = จ.เชียงใหม่",
    "จังหวัดตรัง ; จ.ตรัง": "จังหวัดตรัง = จ.ตรัง",
    "จังหวัดตราด ; จ.ตราด": "จังหวัดตราด = จ.ตราด",
    "จังหวัดตาก ; จ.ตาก": "จังหวัดตาก = จ.ตาก",
    "จังหวัดนครนายก ; จ.นครนายก": "จังหวัดนครนายก = จ.นครนายก",
    "จังหวัดนครปฐม ; จ.นครปฐม": "จังหวัดนครปฐม = จ.นครปฐม",
    "จังหวัดนครพนม ; จ.นครพนม": "จังหวัดนครพนม = จ.นครพนม",
    "จังหวัดนครราชสีมา ; จ.นครราชสีมา": "จังหวัดนครราชสีมา = จ.นครราชสีมา",
    "จังหวัดนครศรีธรรมราช ; จ.นครศรีธรรมราช": "จังหวัดนครศรีธรรมราช = จ.นครศรีธรรมราช",
    "จังหวัดนครสวรรค์ ; จ.นครสวรรค์": "จังหวัดนครสวรรค์ = จ.นครสวรรค์",
    "จังหวัดนนทบุรี ; จ.นนทบุรี": "จังหวัดนนทบุรี = จ.นนทบุรี",
    "จังหวัดนราธิวาส ; จ.นราธิวาส": "จังหวัดนราธิวาส = จ.นราธิวาส",
    "จังหวัดน่าน ; จ.น่าน": "จังหวัดน่าน = จ.น่าน",
    "จังหวัดบึงกาฬ ; จ.บึงกาฬ": "จังหวัดบึงกาฬ = จ.บึงกาฬ",
    "จังหวัดบุรีรัมย์ ; จ.บุรีรัมย์": "จังหวัดบุรีรัมย์ = จ.บุรีรัมย์",
    "จังหวัดปทุมธานี ; จ.ปทุมธานี": "จังหวัดปทุมธานี = จ.ปทุมธานี",
    "จังหวัดประจวบคีรีขันธ์ ; จ.จวบคีรีขันธ์": "จังหวัดประจวบคีรีขันธ์ = จ.จวบคีรีขันธ์",
    "จังหวัดปราจีนบุรี ; จ.ปราจีนบุรี": "จังหวัดปราจีนบุรี = จ.ปราจีนบุรี",
    "จังหวัดปัตตานี ; จ.ปัตตานี": "จังหวัดปัตตานี = จ.ปัตตานี",
    "จังหวัดพระนครศรีอยุธยา ; จ.พระนครศรีอยุธยา": "จังหวัดพระนครศรีอยุธยา = จ.พระนครศรีอยุธยา",
    "จังหวัดพะเยา ; จ.พะเยา": "จังหวัดพะเยา = จ.พะเยา",
    "จังหวัดพังงา ; จ.พังงา": "จังหวัดพังงา = จ.พังงา",
    "จังหวัดพัทลุง ; จ.พัทลุง": "จังหวัดพัทลุง = จ.พัทลุง",
    "จังหวัดพิจิตร ; จ.พิจิตร": "จังหวัดพิจิตร = จ.พิจิตร",
    "จังหวัดพิษณุโลก ; จ.พิษณุโลก": "จังหวัดพิษณุโลก = จ.พิษณุโลก",
    "จังหวัดเพชรบุรี ; จ.เพชรบุรี": "จังหวัดเพชรบุรี = จ.เพชรบุรี",
    "จังหวัดเพชรบูรณ์ ; จ.เพชรบูรณ์": "จังหวัดเพชรบูรณ์ = จ.เพชรบูรณ์",
    "จังหวัดแพร่ ; จ.แพร่": "จังหวัดแพร่ = จ.แพร่",
    "จังหวัดภูเก็ต ; จ.ภูเก็ต": "จังหวัดภูเก็ต = จ.ภูเก็ต",
    "จังหวัดมหาสารคาม ; จ.มหาสารคาม": "จังหวัดมหาสารคาม = จ.มหาสารคาม",
    "จังหวัดมุกดาหาร ; จ.มุกดาหาร": "จังหวัดมุกดาหาร = จ.มุกดาหาร",
    "จังหวัดแม่ฮ่องสอน ; จ.แม่ฮ่องสอน": "จังหวัดแม่ฮ่องสอน = จ.แม่ฮ่องสอน",
    "จังหวัดยโสธร ; จ.ยโสธร": "จังหวัดยโสธร = จ.ยโสธร",
    "จังหวัดยะลา ; จ.ยะลา": "จังหวัดยะลา = จ.ยะลา",
    "จังหวัดร้อยเอ็ด ; จ.ร้อยเอ็ด": "จังหวัดร้อยเอ็ด = จ.ร้อยเอ็ด",
    "จังหวัดระนอง ; จ.ระนอง": "จังหวัดระนอง = จ.ระนอง",
    "จังหวัดระยอง ; จ.ระยอง": "จังหวัดระยอง = จ.ระยอง",
    "จังหวัดราชบุรี ; จ.ราชบุรี": "จังหวัดราชบุรี = จ.ราชบุรี",
    "จังหวัดลพบุรี ; จ.ลพบุรี": "จังหวัดลพบุรี = จ.ลพบุรี",
    "จังหวัดลำปาง ; จ.ลำปาง": "จังหวัดลำปาง = จ.ลำปาง",
    "จังหวัดลำพูน ; จ.ลำพูน": "จังหวัดลำพูน = จ.ลำพูน",
    "จังหวัดเลย ; จ.เลย": "จังหวัดเลย = จ.เลย",
    "จังหวัดศรีสะเกษ ; จ.ศรีสะเกษ": "จังหวัดศรีสะเกษ = จ.ศรีสะเกษ",
    "จังหวัดสกลนคร ; จ.สกลนคร": "จังหวัดสกลนคร = จ.สกลนคร",
    "จังหวัดสงขลา ; จ.สงขลา": "จังหวัดสงขลา = จ.สงขลา",
    "จังหวัดสตูล ; จ.สตูล": "จังหวัดสตูล = จ.สตูล",
    "จังหวัดสมุทรปราการ ; จ.สมุทรปราการ": "จังหวัดสมุทรปราการ = จ.สมุทรปราการ",
    "จังหวัดสมุทรสงคราม ; จ.สมุทรสงคราม": "จังหวัดสมุทรสงคราม = จ.สมุทรสงคราม",
    "จังหวัดสมุทรสาคร ; จ.สมุทรสาคร": "จังหวัดสมุทรสาคร = จ.สมุทรสาคร",
    "จังหวัดสระแก้ว ; จ.สระแก้ว": "จังหวัดสระแก้ว = จ.สระแก้ว",
    "จังหวัดสระบุรี ; จ.สระบุรี": "จังหวัดสระบุรี = จ.สระบุรี",
    "จังหวัดสิงห์บุรี ; จ.สิงห์บุรี": "จังหวัดสิงห์บุรี = จ.สิงห์บุรี",
    "จังหวัดสุโขทัย ; จ.สุโขทัย": "จังหวัดสุโขทัย = จ.สุโขทัย",
    "จังหวัดสุพรรณบุรี ; จ.สุพรรณบุรี": "จังหวัดสุพรรณบุรี = จ.สุพรรณบุรี",
    "จังหวัดสุราษฎร์ธานี ; จ.สุราษฎร์ธานี": "จังหวัดสุราษฎร์ธานี = จ.สุราษฎร์ธานี",
    "จังหวัดสุรินทร์ ; จ.สุรินทร์": "จังหวัดสุรินทร์ = จ.สุรินทร์",
    "จังหวัดหนองคาย ; จ.หนองคาย": "จังหวัดหนองคาย = จ.หนองคาย",
    "จังหวัดหนองบัวลำภู ; จ.หนองบัวลำภู": "จังหวัดหนองบัวลำภู = จ.หนองบัวลำภู",
    "จังหวัดอ่างทอง ; จ.อ่างทอง": "จังหวัดอ่างทอง = จ.อ่างทอง",
    "จังหวัดอำนาจเจริญ ; จ.อำนาจเจริญ": "จังหวัดอำนาจเจริญ = จ.อำนาจเจริญ",
    "จังหวัดอุดรธานี ; จ.อุดรธานี": "จังหวัดอุดรธานี = จ.อุดรธานี",
    "จังหวัดอุตรดิตถ์ ; จ.อุตรดิตถ์": "จังหวัดอุตรดิตถ์ = จ.อุตรดิตถ์",
    "จังหวัดอุทัยธานี ; จ.อุทัยธานี": "จังหวัดอุทัยธานี = จ.อุทัยธานี",
    "จังหวัดอุบลราชธานี ; จ.อุบลราชธานี": "จังหวัดอุบลราชธานี = จ.อุบลราชธานี",
    "จัดอีเว้นท์": "จัดงานอีเว้นท์ ; จัดอีเว้นท์",
    "จาบัล ; จาบัลย์": "จาบัล = จาบัลย์",
    "จุลชีววิทยาของดิน": "จุลชีววิทยาของดิน ; จุลชีววิทยาทางดิน",
    "ชรงำ ; ชระงำ": "ชรงำ = ชระงำ",
    "ชรแลง ; ชระแลง": "ชรแลง = ชระแลง",
    "ชอง ; ฌอง": "ชอง = ฌอง",
    "ชั่วโมงก่อน (… ชั่วโมงก่อน) ; … ชม.ก่อน": "ชั่วโมงก่อน = ชม.ก่อน",
    "ชาร์ลส์ ; ชาลส์": "ชาร์ลส์ = ชาลส์",
    "แชร์ ; แช": "แชร์ = แช",
    "โชก": "โชก ; โชกๆ = โชก ๆ",
    "ซูริก ; ซูริค": "ซูริก = ซูริค",
    "เซรามิค ; เซรามิก": "เซรามิค = เซรามิก",
    "ไซซ์ ; ไซส์": "ไซซ์ = ไซส์",
    "ดุ่ย ; ดุ่ย า": "ดุ่ย",
    "ดุษิต ; ดุสิต": "ดุษิต = ดุสิต",
    "เด็กหญิง ; ด.ญ": "เด็กหญิง = ด.ญ",
    "โดมินิค ; โดมินิก": "โดมินิค = โดมินิก",
    "ตกคลัก ; ตกคลั่ก": "ตกคลัก = ตกคลั่ก",
    "ตฤบ ; ตฤป": "ตฤบ = ตฤป",
    "ตฤๅ ; ตรี": "ตฤๅ = ตรี",
    "ติ๋ง": "ติ๋ง ; ติ๋งๆ = ติ๋ง ๆ",
    "ติด ๆ กัน ; ติดๆกัน": "ติด ๆ กัน = ติดๆกัน",
    "ตุ๊กตุ๊ก ; ตุ๊ก ๆ = ตุ๊กๆ": "ตุ๊กตุ๊ก = ตุ๊ก ๆ = ตุ๊กๆ",
    "ตุล ; ตุลย์": "ตุล = ตุลย์",
    "ตู้เสบียงรถไฟ": "ตู้เสบียงรถไฟ ; ตู้เสบียง",
    "ทงัน ; ทะงัน": "ทงัน = ทะงัน",
    "ทชี ; ธชี": "ทชี = ธชี",
    "ทรงเครื่องใหญ่": "ทรงเครื่องใหญ่ ; ทรงประเครื่องใหญ่",
    "ทอมัส ; โทมัส ; โธมัส": "ทอมัส = โทมัส = โธมัส",
    "ท่าอากาศยานเวียนนา = ท่าอากาศยานนานาชาติเวียนนา": "ท่าอากาศยานเวียนนา ; ท่าอากาศยานนานาชาติเวียนนา",
    "ทิฐิ ; ทิฏฐ": "ทิฐิ = ทิฏฐ",
    "เทเวศ ; เทเวศร์ ; เทเวศวร์": "เทเวศ = เทเวศร์ = เทเวศวร์",
    "เทอร์มินอล 21 ; เทอร์มินอล ทเวนตีวัน": "เทอร์มินอล 21 = เทอร์มินอล ทเวนตีวัน",
    "ไทลื้อ ;ไตลื้อ": "ไทลื้อ =ไตลื้อ",
    "ธิดา ถาวรเศรษฐ์ ; ธิดา ถาวรเศรษฐ": "ธิดา ถาวรเศรษฐ์ = ธิดา ถาวรเศรษฐ",
    "นกนางแอ่นแปซิฟิก ; นกนางแอ่นแปซิฟิค": "นกนางแอ่นแปซิฟิก = นกนางแอ่นแปซิฟิค",
    "นกอินทรีทุ่งหญ้าสเต็ป ; นกอินทรีทุ่งหญ้าสเต็ปป์": "นกอินทรีทุ่งหญ้าสเต็ป = นกอินทรีทุ่งหญ้าสเต็ปป์",
    "น็อก ; น็อค": "น็อก = น็อค",
    "นอต ; น็อต": "น็อต",
    "นักโลหกรรม ; นักโลหะกรรม": "นักโลหกรรม = นักโลหะกรรม",
    "น้ำมนต์ ; น้ำมนตร์": "น้ำมนต์ = น้ำมนตร์",
    "นิวัต ; นิวัตน์": "นิวัต = นิวัตน์",
    "เนืองนิตย์ ; เนืองนิจ": "เนืองนิตย์ = เนืองนิจ",
    "บทบาทของไทย": "บทบาทของไทย ; บทบาทของประเทศไทย",
    "ประเวศ ; ประเวศน์": "ประเวศ = ประเวศน์",
    "ปลากะพงขาว ; [ปลากระพงขาว]": "ปลากะพงขาว",
    "ปลากะพงแดง ; [ปลากระพงแดง]": "ปลากะพงแดง",
    "ปั๊มแอลพีจี ; ปั๊ม LPG": "ปั๊มแอลพีจี = ปั๊ม LPG",
    "โปร ; โปรฯ": "โปร = โปรฯ",
    "โปรไบโอติก ; โปรไบโอติกส์": "โปรไบโอติก = โปรไบโอติกส์",
    "ไปกลับ ; ไป-กลับ": "ไปกลับ = ไป-กลับ",
    "ผลานิสงส์ ; ผลานิสงฆ์": "ผลานิสงส์ = ผลานิสงฆ์",
    "พอเป็นกระษัย ; พอเป็นกระสัย": "พอเป็นกระษัย = พอเป็นกระสัย",
    "พัฒน์พงศ์ ; พัฒน์พงศ์": "พัฒน์พงศ์ = พัฒน์พงศ์",
    "พิธีเปิดกีฬาโอลิมปิก": "พิธีเปิดกีฬาโอลิมปิก ; พิธีกีฬาโอลิมปิก",
    "พิพิธภัณฑ์สถานแห่งชาติ บ้านเก่า ; พิพิธภัณฑ์สถานแห่งชาติบ้านเก่า": "พิพิธภัณฑ์สถานแห่งชาติ บ้านเก่า = พิพิธภัณฑ์สถานแห่งชาติบ้านเก่า",
    "พีดีเอฟ ; PDF": "พีดีเอฟ = PDF",
    "โพเทนซิโอมิเตอร์แบบเชิงเส้น": "โพเทนชิโอมิเตอร์แบบเชิงเส้น ; โพเทนซิโอมิเตอร์แบบเชิงเส้น",
    "เฟิน ; เฟิร์น": "เฟิน = เฟิร์น",
    "ภัต ; ภัตร": "ภัต = ภัตร",
    "ภาษาไทลื้อ ; ภาษาไตลื้อ": "ภาษาไทลื้อ = ภาษาไตลื้อ",
    "โภช ; โภชย์": "โภช = โภชย์",
    "มนุษยสัมพันธ์ ; มนุษย์สัมพันธ์": "มนุษยสัมพันธ์ = มนุษย์สัมพันธ์",
    "มอร์ตาเดลลา ; มอร์ทาเดลลา": "มอร์ตาเดลลา = มอร์ทาเดลลา",
    "ม่อห้อม; ม่อฮ่อม": "ม่อห้อม= ม่อฮ่อม",
    "มะแข่น ; [บ่าแข่น] ; [มะแขว่น]": "มะแขว่น = มะแข่น = บ่าแข่น",
    "มาตรฐานระดับระหว่างประเทศ": "มาตรฐานระดับระหว่างประเทศ ; มาตรฐานระหว่างประเทศ",
    "มาตรา 44 ; ม. 44": "มาตรา 44 = ม. 44",
    "มาร์กาเร็ต ; มากาเร็ด": "มาร์กาเร็ต = มากาเร็ด",
    "เมืองทอง ยูไนเต็ด ; SCG เมืองทอง": "เมืองทอง ยูไนเต็ด ; เมืองทอง",
    "เมืองปาน": "เมืองปาน ; อำเภอเมืองปาน = อ.เมืองปาน",
    "แม่น้ำเมิซ = แม่น้ำมิวส": "แม่น้ำเมิซ ; แม่น้ำมิวส",
    "ไม้แบด ; ไม้แบดฯ": "ไม้แบด = ไม้แบดฯ",
    "ไม้พะยุง ; ไม้พยุง": "ไม้พะยุง = ไม้พยุง",
    "ยนต์ ; ยนตร์": "ยนต์ = ยนตร์",
    "ยาพารา ; ยาพาราฯ": "ยาพารา = ยาพาราฯ",
    "ยิฏฐะ ; ยิฐะ": "ยิฏฐะ = ยิฐะ",
    "ยี้ ; ยี้ !": "ยี้ = ยี้ !",
    "ยี่สาน ; ยี่ส่าน": "ยี่สาน = ยี่ส่าน",
    "ยุนนาน ; หยุนหนาน": "ยุนนาน = หยุนหนาน",
    "ยูเอสบี ; USB": "ยูเอสบี = USB",
    "ระบบนิเวศ ; ระบบนิเวศน์": "ระบบนิเวศ = ระบบนิเวศน์",
    "รัฐาธิปัตย์ ; รัฏฐาธิปัตย์": "รัฐาธิปัตย์ = รัฏฐาธิปัตย์",
    "ราชกิจจา ; ราชกิจจาฯ": "ราชกิจจา = ราชกิจจาฯ",
    "เรื่องจิ๊บ ๆ = เรื่องจิ๊บๆ ; เรื่องจิ๊บจิ๊บ = เรื่องจิ๊บ จิ๊บ": "เรื่องจิ๊บ ๆ = เรื่องจิ๊บๆ = เรื่องจิ๊บจิ๊บ = เรื่องจิ๊บ จิ๊บ",
    "โรงงานเซรามิค ; โรงงานเซรามิก": "โรงงานเซรามิค = โรงงานเซรามิก",
    "โรจ ; โรจน์": "โรจ = โรจน์",
    "ลาสเวกัส": "ลาสเวกัส ; เวคัส",
    "ลิเทียม ; ลิเธียม": "ลิเทียม = ลิเธียม",
    "ลูกเอ็น ; ลูกเอ็ล": "ลูกเอ็น = ลูกเอ็ล",
    "เลอม็องส์ ; เลอม็อง": "เลอม็องส์ = เลอม็อง",
    "โลซาน ; โลซานน์": "โลซาน = โลซานน์",
    "โลหกรรม ; โลหะกรรม": "โลหกรรม = โลหะกรรม",
    "วณิพก ; วนิพก": "วณิพก = วนิพก",
    "วนิพก ; วณิพก": "วนิพก = วณิพก",
    "วรณัย ; วรนัย": "วรณัย = วรนัย",
    "วันที่ 1 ม.ค. ; วันที่ 1 มกราคม": "วันที่ 1 ม.ค. = วันที่ 1 มกราคม",
    "วันละ 2 ครั้ง ; วันละสองครั้ง": "วันละ 2 ครั้ง = วันละสองครั้ง",
    "ว้าว ; ว้าว!": "ว้าว = ว้าว!",
    "วิทยาลัยเทคนิค ; เทคนิค": "วิทยาลัยเทคนิค ; วิทยาลัยเทค ; เทคนิค",
    "วินโดวส์ 10 ; วินโดวส์สิบ": "วินโดวส์ 10 = วินโดวส์สิบ",
    "วินโดวส์ 11 ; วินโดวส์ สิบเอ็ด": "วินโดวส์ 11 = วินโดวส์ สิบเอ็ด",
    "วินโดวส์ 7 ; วินโดวส์เซเว่น": "วินโดวส์ 7 = วินโดวส์เซเว่น",
    "วินโดวส์ 8 ; วินโดวส์แปด": "วินโดวส์ 8 = วินโดวส์แปด",
    "วินโดวส์ XP ; วินโดวส์เอกซ์พี": "วินโดวส์ XP = วินโดวส์เอกซ์พี",
    "วิลลี่วิลลี่ ; วิลลี-วิลลี": "วิลลี่วิลลี่ = วิลลี-วิลลี",
    "วีรกร ; วีระกร": "วีรกร = วีระกร",
    "วุฒิสมาชิกสหรัฐอเมริกา ; วุฒิสมาชิกสหรัฐฯ": "วุฒิสมาชิกสหรัฐอเมริกา = วุฒิสมาชิกสหรัฐฯ",
    "โว้ย ; โว้ย !": "โว้ย = โว้ย !",
    "สถานการณ์ โควิด-19 ; สถานการณ์ COVID-19": "สถานการณ์ โควิด-19 = สถานการณ์ COVID-19",
    "สนามบินเจเอฟเค ; สนามบิน JFK": "สนามบินเจเอฟเค = สนามบิน JFK",
    "สมเด็จพระนโรดม สีหนุ ; สมเด็จพระนโรดมสีหนุ": "สมเด็จพระนโรดม สีหนุ = สมเด็จพระนโรดมสีหนุ",
    "สมบัติ ; สมบัด": "สมบัติ = สมบัด",
    "สฤษฎิ ; สฤษฎี ; สฤษฏ์": "สฤษฎิ = สฤษฎี = สฤษฏ์",
    "สหชาติ ; สหชาต": "สหชาติ = สหชาต",
    "สองสัปดา ; 2 สัปดา": "สองสัปดา = 2 สัปดา",
    "สายพันธุ์เดลต้า ; สายพันธุ์ Delta": "สายพันธุ์เดลต้า = สายพันธุ์ Delta",
    "สายพันธุ์มิว ; สายพันธุ์ Mu": "สายพันธุ์มิว = สายพันธุ์ Mu",
    "สายพันธุ์โอมิครอน ; สายพันธุ์โอไมครอน ; สายพันธุ์ Omicron": "สายพันธุ์โอมิครอน ; สายพันธุ์โอไมครอน = สายพันธุ์ Omicron",
    "สารวัด ; สารวัตร": "สารวัด = สารวัตร",
    "สิรินุช ; ศิรินุช": "สิรินุช = ศิรินุช",
    "สุญตา ; สุญญตา": "สุญตา = สุญญตา",
    "สุนีย์ ; สุนี": "สุนีย์ = สุนี",
    "สู้สู้ ; สู้ ๆ = สู้ๆ": "สู้สู้ = สู้ ๆ = สู้ๆ",
    "เสื้อหม้อห้อม ; เสื้อหม้อฮ่อม": "เสื้อหม้อห้อม = เสื้อหม้อฮ่อม",
    "หนึ่งครั้ง ; 1 ครั้ง": "หนึ่งครั้ง = 1 ครั้ง",
    "หม่อมเจ้าจุลเจิม ยุคล (ท่านใหม่) ; ต.ม.จ.จุลเจิม ยุคล": "หม่อมเจ้าจุลเจิม ยุคล = ต.ม.จ.จุลเจิม ยุคล (ท่านใหม่)",
    "หมายเลข 1 ; หมายเลขหนึ่ง": "หมายเลข 1 = หมายเลขหนึ่ง",
    "เหลือล้น ; เหลือหลาย ; เหลือแหล่": "เหลือล้น",
    "อดุล ; อดุลย์": "อดุล = อดุลย์",
    "อปมงคล ; อัปมงคล": "อปมงคล = อัปมงคล",
    "อภิวาท ; อภิวาทน์": "อภิวาท = อภิวาทน์",
    "อลาสก้า": "อลาสก้า = อลาสคา ; อแลสกา",
    "อลิสซา ; อลิซซา": "อลิสซา = อลิซซา",
    "อ๋อ ; อ๋อ!": "อ๋อ = อ๋อ!",
    "อะลุ่มอล่วย ; อะลุ้มอล่วย": "อะลุ่มอล่วย = อะลุ้มอล่วย",
    "อ้า ; อ้าาา": "อ้า = อ้าาา",
    "อ้าขาผวาปีก ; อ้าขาพวาปีก": "อ้าขาผวาปีก = อ้าขาพวาปีก",
    "อาณาจักรทวาราวดี": "อาณาจักรทวาราวดี ; อาณาจักรทวารวดี",
    "อาถรรพ์ ; อาถรรพณ์": "อาถรรพ์ = อาถรรพณ์",
    "อาถรรพ์ ; อาถรรพณ์": "อาถรรพ์ = อาถรรพณ์",
    "อามิส ; อามิษ": "อามิส = อามิษ",
    "อำนิฐ ; อำนิษฐ์": "อำนิฐ = อำนิษฐ์",
    "อิฏฐ- ; อิฐ-": "อิฏฐ- = อิฐ-",
    "อี๊ ; อี๊ ! ; อี้": "อี๊ = อี๊ ! ; อี้",
    "อืม ; อืม!": "อืม = อืม!",
    "อุบลฯ ; อุบล": "อุบลฯ = อุบล",
    "เอ็มบริโอ ; เอมบริโอ": "เอ็มบริโอ = เอมบริโอ",
    "เอส โคล่า": "เอส โคล่า ; เอส",
    "แอนน์ ; แอน": "แอนน์ = แอน",
    "แอพส์ ; แอปฯ": "แอพส์ = แอปฯ",
    "แอร์บัส A320 ; แอร์บัส เอ320": "แอร์บัส A320 = แอร์บัส เอ320",
    "แอร์บัส A330 ; แอร์บัส เอ330": "แอร์บัส A330 = แอร์บัส เอ330",
    "แอร์บัส A350 ; แอร์บัส เอ350": "แอร์บัส A350 = แอร์บัส เอ350",
    "แอร์บัส A380 ; แอร์บัส เอ380": "แอร์บัส A380 = แอร์บัส เอ380",
    "แอสตร้าเซนเนก้า ; แอสตราฯ": "แอสตร้าเซนเนก้า = แอสตราฯ",
    "ไอเคโอ": "ไอเคโอ ; ไอซีเอโอ",
    "ไอ้สัตว์ ; ไอ้สัส": "ไอ้สัตว์ = ไอ้สัส",
    "ฮ็อต ; ฮอต": "ฮ็อต",
    "ฮาร์ลีย์-เดวิดสัน": "ฮาร์ลีย์-เดวิดสัน; ฮาร์ลีย์",
    "โฮมินิด ; โฮมินิดส์": "โฮมินิด = โฮมินิดส์",
    "โฮโมซาเปี้ยน ; โฮโมเซเปียนส์ ; โฮโม เซเปียนส์": "โฮโมซาเปี้ยน ; โฮโมเซเปียนส์ = โฮโม เซเปียนส์",
    "ทอมัส ; โทมัส ; โธมัส": "ทอมัส ; โทมัส = โธมัส",
    "พจนานุกรมฉบับราชบัณฑิตยสถาน พ.ศ. ๒๕๕๔ = พจนานุกรมฉบับราชบัณฑิตยสถาน พ.ศ. 2554": "พจนานุกรมฉบับราชบัณฑิตยสถาน",
    "ประเทศคองโก ประเทศคองโก-บราซซาวิล": "ประเทศคองโก-บราซซาวิล",
    "นกกระทาดงจันทบูรณ์, นกกระทาดงจันทบูร ?": "นกกระทาดงจันทบูรณ์ = นกกระทาดงจันทบูร",
    "คิริบาส ; คิริบาติ": "ประเทศคิริบาส ; ประเทศคิริบาติ",
    "ผู้อยู่ในอุปการะ = ผู้อยู่ในอุปการะ": "ผู้อยู่ในความอุปการะ ; ผู้อยู่ในอุปการะ",
    "โมเมนต์ความเฉื่อยชา": "โมเมนต์ความเฉื่อย",
    "ตลาดน้ำวัดลำพญา ; ตลาดน้ำวัดลำพญา": "ตลาดน้ำลำพญา ; ตลาดน้ำวัดลำพญา",
    "มะเนียงน้ำา": "มะเนียงน้ำ",
    "สวัสดิภาพของชาฅิ": "สวัสดิภาพของชาติ",
    "เพลงชาฅิไทย": "เพลงชาติไทย",
    "มูอัมมาร์ กัดดาฟี = มูอัมมาร์ อัล-กัดดาฟี": "มูอัมมาร์ กัดดาฟี ; มูอัมมาร์ อัล-กัดดาฟี",
    "เวกเตอร์ออก": "เวกเตอร์ชี้ออก",
    "สิ่งสิ่งอัศจรรย์อันดับ 8 ของโลก": "สิ่งอัศจรรย์อันดับ 8 ของโลก",
    "สิ่งสิ่งอัศจรรย์": "สิ่งอัศจรรย์",
    "เครือข่ายพลเมืองเน็ต": "พลเมืองเน็ต",
    "ทรงผม MoHawk": "ทรงผมโมฮอว์ก = ทรงผมโมฮอค = ทรงโมฮ๊อก",
    "ประยุทธ์ ปยุตฺโต ; ป.อ. ปยุตฺโต": "ประยุทธ์ ปยุตฺโต ; ป.อ. ประยุทธ์ ปยุตฺโต",
    "กรมทหารมหาดเล็กราชวัลลภรักษาพระองค์ 904": "กรมทหารมหาดเล็กราชวัลลภรักษาพระองค์",
    "https": "สกุลสูง",
    "แก้ออก": "แก้ออก (แก้...ออก)",
    "กรมสอบสวนคดีพิเศษ": "กรมสอบสวนคดีพิเศษ (DSI)",
    "ม.ล.": "ม.ล. (หม่อมหลวง)",
    "ออกกี่โมง (...ออกกี่โมง)": "ออกกี่โมง",
    "หน่อยซิ (...หน่อยซิ)": "หน่อยซิ",
    "เป็นไงบ้าง (...เป็นไงบ้าง)": "เป็นไงบ้าง",
    "ที่ไหน (...ที่ไหน)": "ที่ไหน",
    "แพทองธาร ชินวัตร": "แพทองธาร ชินวัตร (อุ๊งอิ๊งค์)",
    "พ.ศ. …": "พ.ศ. (พุทธศักราช)",
    "สมาชิกสภาผู้แทนราษฎร": "สมาชิกสภาผู้แทนราษฎร (ส.ส)",
    "สรรเสริญ แก้วกำเนิด": "สรรเสริญ แก้วกำเนิด (ไก่อู)",
    "อำพล ตั้งนพกุล (อากง , อากง SMS)": "อำพล ตั้งนพกุล (อากง ; อากง SMS)",
    "ท่าเรือ ; อำเภอ = อ.": "ท่าเรือ ; อำเภอท่าเรือ = อ.ท่าเรือ",
    "บ้านกรวด ; อำเภอ = อ.": "บ้านกรวด ; อำเภอบ้านกรวด = อ.บ้านกรวด",
    "โรงพยาบาลพระมงกุฏเกล้า ; โรงพยาบาลพระมงกุฏเกล้า": "โรงพยาบาลพระมงกุฏเกล้า ; โรงพยาบาลพระมงกุฏ",
    "ตุ๊กตาลูกเทพ ; ตุ๊กตาลูกเทพ": "ตุ๊กตาลูกเทพ ; ลูกเทพ",
    "ผู้เชี่ยวชาญภาษาสันสกฤต ; ผู้เชี่ยวชาญภาษาสันสกฤต": "ผู้เชี่ยวชาญภาษาสันสกฤต ; ผู้เชี่ยวชาญด้านภาษาสันสกฤต",
    "บรรยากาศของโลก ; บรรยากาศของโลก": "บรรยากาศของโลก ; บรรยากาศโลก",
    "อาชญาวิทยา ; อาชญาวิทยา": "อาชญาวิทยา",
    "อาชญาวิทยา = อาชญาวิทยา": "อาชญาวิทยา",

    # TONELESS
    "Rōngphayābān Phra Mongkut Klāo ; Rōngphayābān Phra Mongkut Klāo":
    "Rōngphayābān Phra Mongkut Klāo ; Rōngphayābān Phra Mongkut",

    "nā- ; nā -": "nā-",
    "nānā chāt": "nānāchāt",
    "Amphon Tangnopphakun (Ākong)": "Amphon Tangnopphakun (Ākong ; Ākong SMS)",
    "maklam nū": "maklam tā nū",
    "Rēt Būl ; Krathing Daēng)": "Rēt Būl ; Krathing Daēng",
    "thēwanākharī (= thēwanākhrī)": "thēwanākharī = thēwanākhrī",
    "nākkharāt klet": "nākkharāt klet nāmtān",
    "song phom song hit": "song phom hit",
    "Sátāt doe Frøng": "Satāt doe Frøng",
    "Phithīsān Montrīøl": "Phithīsān Montrī-øl",
    "phāsā khrīøl": "phāsā khrī-øl",
    "Saēn Dīēkō": "Saēn Dī-ēkō",
    "Lui Blēriō": "Lui Blēri-ō",
    "nok pāksǿm Sáwinhō": "nok pāksǿm Sawinhō",
    "Mǿm Naritsa Jakkraphong": "Mǿm Rātchawong Naritsa Jakkraphong",
    "latthi nīō-nāsī": "latthi nī-ō-nāsī",
    "amareuttarot": "amarittarot = amareuttarot",
    "amarit ; amareut": "amarit = amareut",
    "aparā ; apparā": "aparā = apparā",
    "Ārittōtoēn = Arittōtoēn": "Ārittōtoēn ; Arittōtoēn",
    "baētmintan = baetmintan": "baētmintan ; baetmintan",
    "Bōing": "Bō-ing",
    "khreūangbin Bōing": "khreūangbin Bō-ing",
    "Bōing jet-jet-jet": "Bō-ing jet-jet-jet",
    "Bōing jet-paēt-jet Drīmlainoē": "Bō-ing jet-paēt-jet Drīmlainoē",
    "Bōing jet-sām-jet": "Bō-ing jet-sām-jet",
    "Bōing jet-sī-jet": "Bō-ing jet-sī-jet",
    "būasāiting": "būasāiting ; būasāithing",
    "chaithāo": "chaithāo ; chaithāo",
    "chan matthayomseuksā ; chan matthayommaseuksā": "chan matthayomseuksā = chan matthayommaseuksā",
    "chāti- ; chātti-": "chāti- = chātti-",
    "chātti- ; chāti-": "chātti- = chāti-",
    "china- ; chinna-": "china- = chinna-",
    "chinna- ; china-": "china- = chinna-",
    "Daēllas = Daēnlas ; Dēllas ; Dallas": "Daēllas = Daēnlas ; Dallas",
    "Dapboēn-Yū ; dapboēn-yū": "Dapboēn-Yū = dapboēn-yū",
    "dūlaē hai dī ; dūlaē ... hai dī": "dūlaē hai dī (dūlaē ... hai dī)",
    "ēkā": "ēkā ; ēkā",
    "euk ; euk-euk": "euk ; euk ; euk-euk",
    "hahāi": "hahāi ; hahāi",
    "Hansā Røsatǿk ; Hansā Røsatǿk": "Hansā Røsatǿk",
    "Hēnrī Føt": "Hēnrī Føt ; Hēnrī Føt",
    "Hēnrī": "Hēnrī ; Hēnrī",
    "høhaē": "høhaē ; høhaē",
    "høi kāpdīo": "høi kāpdīo ; høi kāpdīo",
    "hǿng dōisān khreūangbin": "hǿng dōisān khreūangbin ; hǿng dōisān",
    "hongsapōdok": "hongsapōdok ; hongsapōdok",
    "īkho": "īkho ; īkho",
    "jaekket": "jaekket ; jaēkket",
    "jakkalaen": "jakkalaen ; jakkalaen",
    "jaralāt": "jaralāt ; jaralāt",
    "jøng phān Intoēnet": "jøng phān Intoēnet ; jøng phān Inthoēnet",
    "jōngkhreum": "jōngkhreum ; jōngkhreum",
    "jøralūang": "jøralūang ; jøralūang",
    "kabanglom ; [krabanglom]": "kabanglom",
    "kamrāk": "kamrāk ; kamrāk",
    "kān- ; kan -": "kān- = kan-",
    "kaokeuk": "kaokeuk ; kaokeuk",
    "kāpdīo": "kāpdīo ; kāpdīo",
    "keung … ; keung-": "keung",
    "khaep": "khaep ; khaēp",
    "khak ; khak-khak": "khak ; khak ; khak-khak",
    "khati anāthippatai ; khati anāthipatai": "khati anāthippatai = khati anāthipatai",
    "Khē ; khē": "Khē = khē",
    "khī ; khī-": "khī-",
    "khøndō = khǿndō": "khøndō ; khøndōminīem",
    "Khøngkō ; Khøngkō Brātsāwin": "Khøngkō Brātsāwin",
    "Khøstā Rikā ; Khøttā Rikā": "Khøstā Rikā = Khøttā Rikā",
    "Khōwit sip-kāo ; Khōwit naīnthīn": "Khōwit sip-kāo = Khōwit naīnthīn",
    "khrēngkhram": "khrēngkhram ; khrēngkhrā",
    "Khwaēng Sawannakhēt": "Khwaēng Sawannakhēt ; Khwaēng Suwannakhēt",
    "Kōnkātā ; Kōlkātā": "Kōnkātā = Kōlkātā",
    "krabā": "krabā ; krabā ; krabā",
    "kradaek-kradaek": "kradaek-kradaek ; kradaēk-kradaēk",
    "krajøng-ngǿng": "krajøng-ngǿng ; krajøng-ngǿng",
    "krajup": "krajup ; krajup",
    "kramaep ; kramaep-kramaep ; [kramaēp]": "kramaep ; kramaep-kramaep",
    "kramaep = kramaep-kramaep": "kramaep ; kramaep-kramaep",
    "krapukluk": "krapukluk ; krapukluk",
    "kratip": "kratip ; kratip",
    "Krēta": "Krēta ; Krēta",
    "krik": "krik ; krik",
    "lāpa- ; lāp-": "lāpa- = lāp-",
    "makhaen ; [mākhaen] ; [makhwaen]": "makhwaen = makhwaen = mākhaen",
    "Māksoēi ; Māsaē": "Māksoēi",
    "mak khīen phit pen kham wā “ ...”": "mak khīen phit pen kham wā",
    "Manmoē ; Malmoē": "Manmoē = Malmoē",
    "mēlōdikā": "mēlōdikā ; mēlōdikā",
    "mētābøliseum ; mēthaēbøliseum": "mētābøliseum ; mētābøliseum ; mēthaēbøliseum",
    "Meūangthøng Yūnaitet": "Meūangthøng Yūnaitet ; Meūangthøng",
    "meūtteū": "meūtteū ; meūtteū",
    "meūtteutteū": "meūtteutteū ; meūtteutteū",
    "mikha": "mik ; mikha",
    "Monlarat Khaēlifønīa": "Rat Khaēlifønīa",
    "Monlarat Luisīana": "Rat Luisīana",
    "Monthon Yūnnān": "Monthon Yūnnān ; Monthon Yūnnān",
    "mūan lō som jut dam": "mūan lō som jut dam ; mūan lō jut dam",
    "nām amarit ; nām amareut": "nām amarit = nām amareut",
    "neung lān ; lān ; lān neung": "neung lān = lān",
    "neung meūn ; meūn ; meūn neung": "neung meūn = meūn",
    "neung phan ; phan ; phan neung": "neung phan = phan",
    "neung røi ; røi ; røi neung": "neung røi = røi",
    "neung saēn ; saēn ; saēn neung": "neung saēn = saēn",
    "ngak-ngak": "ngak-ngak ; ngak-ngak",
    "ngok-ngok": "ngok-ngok ; ngok-ngok",
    "Niko": "Niko ; Niko",
    "nǿk-ao": "nǿk-ao ; nǿk-ao",
    "ō-ūat": "ō-ūat ; ō-ūat",
    "ōhō": "ōhō ; ōhō",
    "ōi": "ōi ; ōi",
    "øk kī mōng ; … øk kī mōng": "øk kī mōng (… øk kī mōng)",
    "ōthōng": "ōthōng ; ōthōng",
    "Øtkā ; Øskā": "Øtkā = Øskā",
    "pen ngai bāng ; ... pen ngai bāng": "pen ngai bāng (… pen ngai bāng)",
    "pet chēldak ; pet chēndak": "pet chēldak = pet chēndak",
    "phai thārō": "phai thārō ; phai thārō",
    "phālsā ; phānsā": "phālsā = phānsā",
    "phāthīnōjēnēsit": "phāthīnōjēnēsit ; phāthīnōjēnīsit",
    "phēsatcha- ; phēsat-": "phēsatcha- = phēsat-",
    "Phøthotdam ; Phǿtsadam": "Phøthotdam = Phǿtsadam",
    "Pisā": "Pisā ; Pisā",
    "plā kaphong daēng ; [plā kraphong daēng]": "plā kaphong daēng",
    "plā kaphong khāo ; [plā kraphong khāo]": "plā kaphong khāo",
    "pōk": "pōk ; pōk",
    "Prathēt Khōlambīa ; Prathēt Khōlømbīa": "Prathēt Khōlambīa = Prathēt Khōlømbīa",
    "Prathēt Khøngkō ; Prathēt Khøngkō Brātsāwin": "Prathēt Khøngkō Brātsāwin",
    "Prathēt Khøstā Rikā ; Prathēt Khøttā Rikā": "Prathēt Khøstā Rikā = Prathēt Khøttā Rikā",
    "prīa": "prīa ; prīa",
    "Rat Theksat = Rat Theksas": "Rat Thēksat = Rat Thēksas ; Rat Theksat = Rat Theksas",
    "riprī": "riprī ; riprī",
    "Rōdrikō": "Rōdrīkō ; Rōdrikō",
    "røi et ; neung røi et ; neung roi neung": "røi et = neung røi et",
    "røi kāosip-kāo ; røi kāo-kāo": "røi kāosip-kāo",
    "rōt ; rōtha": "rāt = rātha",
    "Rǿtthoēhaēm Yūnaitet": "Rǿtthoēhaēm Yūnaitet ; Rǿtthoēhaēm",
    "ruprū": "ruprū ; ruprū",
    "sāma- ; sāmma-": "sāma- = sāmma-",
    "saranakhom = saranākhom": "saranakhom ; saranākhom",
    "satawat thī .. ; = sattawat thī ...": "satawat thī .. = sattawat thī ...",
    "satburut ; sattaburut": "satburut = sattaburut",
    "Sāthāranarat Khøstā Rikā ; Sāthāranarat Khøttā Rikā": "Sāthāranarat Khøstā Rikā = Sāthāranarat Khøttā Rikā",
    "satheūoen": "satheūoen ; satheūoen",
    "singthībongchīthāngphūmisāt": "singthībongchīthāngphūmisāt ; singbongchīthāngphūmisāt",
    "sōk- ; sōkka-": "sōk- = sōkka-",
    "suppoēkhā = sūpoēkhā": "suppoēkhā ; sūpoēkhā",
    "Surachai Dānwattanānusøn = Surachai Saē Dān": "Surachai Dānwattanānusøn ; Surachai Saē Dān",
    "sūtsāt": "sūtsāt ; sūtsāt",
    "takaē": "takaē ; takaē",
    "Talātlaksap Tōrøntō": "Talātlaksap Tōrøntō ; Talātlaksap Thōrøntō",
    "teutteū": "teutteū ; teutteū",
    "Thanon Phra Rām Thī Kāo ; Phra Rām Thī Kāo": "Thanon Phra Rām Thī Kāo",
    "Thanon Phra Rām Thī Sī ; Phra Rām Thī Sī": "Thanon Phra Rām Thī Sī",
    "Theksat = Theksas": "Thēksat = Thēksas ; Theksat = Theksas",
    "upāthān ; uppāthān": "upāthān = uppāthān",
    "utthat ; uthathat": "utthat = uthathat",
    "Wan Hālōwīn": "Wan Hālōwīn ; Wan Halōwīn",
    "Winnī doē Phū ; Mī Phū": "Winnī doē Phū",
    "witthayālai thēknik ; วิทยาลัยเทค ; thēknik": "witthayālai thēknik ; witthayālai thēk ; thēknik",
    "wøra- ; wara-": "wøra- = wara-",
    "yāt phīnøng ; yāttiphīnøng": "yāt phīnøng = yāttiphīnøng",
    "Yongwut Yutthawong": "Yongyut Yutthawong",
    "yīo khēstrēl ; yīo khēsatrēn": "yīo khēstrēl = yīo khēsatrēn",
    "rōk klūa sadaēng waep-waep": "rōk klūa saēng waep-waep",
    "Photjanānukrom Chabap Rātchabandittayasathān Phø.Sø. Søng Phan Hā Røi Hāsip-sī": "Photjanānukrom Chabap Rātchabandittayasathān",
    "Sanāmbin Sanāmbin Chāng-ngī": "Sanāmbin Chāng-ngī",
    "kēngkhēng": "kēngkhēng ; kēngkhēng",
    "dāo Siriut": "dāo Siri-ut",
    "Alfā Rōmēø = Anfā Rōmēø": "Alfā Rōmē-ø = Anfā Rōmē-ø",
    "anukrom haiphoējīømētrik": "anukrom haiphoējī-ømētrik",
    "børisat khrēdit føngsiē": "børisat khrēdit føngsi-ē",
    "bīa Līō ; Līō": "bīa Lī-ō ; Lī-ō",
    "āthisoērødas jāriyē": "āthisoērøt jāriyē",
    "āthisoērødas thailaēndikhas": "āthisoērøt thailaēndikhas",
    "hǿng satūdiō": "hǿng satūdi-ō",
    "kaēt sanfoē-daiǿksai": "kaēt sanfoē-dai-ǿksai",
    "kān chāi satoēriōkrāfik": "kān chāi satoēri-ōkrāfik",
    "fangchan Møebiut = fangchan Møebius": "fangchan Moēbi-ut = fangchan Moēbi-us",
    "kān plaēng Møebius": "kān plaēng Moēbi-ut = kān plaēng Moēbi-us",
    "thaēp Møebiut = thaēp Møebius": "thaēp Moēbi-ut = thaēp Moēbi-us",
    "kāt khābøn daiøksai": "kāt khābøn dai-øksai",
    "kāt sanfoē-daiǿksai": "kāt sanfoē-dai-øksai",
    "khlip wīdīō = khlip widīō": "khlīp wīdī-ō = khlip wīdī-ō",
    "klǿngthāiphāp rāi laīet sūng": "klǿngthāiphāp rāi la-īet sūng",
    "klǿng wīdīō = klǿng widīō": "klǿng wīdī-ō = klǿng wīdī-ō",
    "klūay kaliøng": "klūay kali-øng",
    "klūay maniøng": "klūay mani-øng",
    "dāothīem Thīøs": "dāothīem Thī-øs",
    "Ēliō Di Rūpō": "Ēli-ō Di Rūpō",
    "thēp wīdīō = thēp  widīō": "thēp wīdī-ō = thēp widī-ō",
    "thanākhān sátem sel": "thanākhān satem sel",
    "Sūpoē Māriō": "Sūpoē Māri-ō",
    "Rōmeō lae Jūlīet": "Rōme-ō lae Jūlīet",
    "ratsamī iøn": "ratsamī i-øn",
    "rangsī antrāwaiōlēt": "rangsī antrāwai-ōlēt",
    "Mahāwitthayālai Sīahēmin": "Mahāwitthayālai Sīamoēn",
    "yūrēnīem hēksāflūørai = yūrēnīem hēksaflūørai": "yūrēnīem hēksāflū-ørai = yūrēnīem hēksaflū-ørai",
    "phāp satoēriōkraēm": "phāp satoēri-ōkraēm",
    "Boētan Albīen ; Boētan Albīen": "Boētan Albīen ; Boētan",
    "deūoen karakadākhom / deūoen karakkadākhom ; deūoen karakadā": "deūoen karakadākhom = deūoen karakkadākhom ; deūoen karakadā",
    "krāp sikmøi": "krāp baēp sikmøi",
    "Lūang Phūthūat ; Lūang Phø Thūat (yīep nām thalē jeūt)": "Lūang Phūthūat ; Lūang Phø Thūat yīep nām thalē jeūt",
    "Maēriøt Hōtēl = Maēriøt Hōtēo": "Maēri-øt Hōtēl = Maēri-øt Hōtēo",
    "bai songmøp": "bai songmøp sinkha",
    "bāng khon bøk …": "bāng khon bøk wā …",
    "chōp long yang yāng rūatreo": "chōp long yāng rūatreo",
    "dai-ōt insī (Ō-Aēl-Ī-Dī)": "dai-ōt insī pleng saēng (Ō-Aēl-Ī-Dī)",
    "khaē søng nāthī": "khaē søng khon",
    "kham athibā rāiwichā": "kham athibāi rāiwichā",
    "khon tāseūa døk": "khon tāseūa døk yai",
    "khwām jam janrai": "khwām janrai",
    "nayōbāi raya raya san": "nayōbāi raya san",
    "Phraphuttharūp samrit samai": "Phraphuttharūp samrit samai Sīwichai",
    "plak phūang baēp mī": "plak phūang baēp mī sawit",
    "Utthayān Sa Nāng Manōrā": "Wana-utthayān Sa Nāng Manōrā",
    "monthon thahān": "monthon thahān bok",
    "yāk dāi khømūn (kīokap)": "yāk dāi khømūn kīokap",
    "phū yū nai khwām uppakāra = phū yū nai (khwām) uppakāra": "phū yū nai khwām uppakāra ; phū yū nai uppakāra",
    "jutsūnklāng khøng khwam": "jutsūnklāng khøng khwamthūang",
    "kham yeūm jāk …": "kham yeūm jāk phāsā …",
    "klum dāo Phoēsiet": "klum dāo Phoēsi-at",
    "klum dāo Fīnik": "klum dāo nok Fīnik",
    "kotmāi Chārīa": "kotmāi Chārī-a",
    "thāi sēlfī": "thāi rūp sēlfī",
    "silwoē aiōdai": "silwoē ai-ōdai",
    "Mahāwitthayālai khaēlifønīa Boēklī": "Mahāwitthayālai Khaēlifønīa Boēklī",
    "Mūammā Katdāfī = Mūammā An Katdāfī": "Mū-ammā Katdāfī ; Mū-ammā An Katdāfī",
    "Prathēt Bēlārut / Prathēt Bēlārus": "Prathēt Bēlārut = Prathēt Bēlārus",
    "Prathēt Bénin": "Prathēt Bēnin",
    "praisanī thōralėk": "praisanī thōralēk",
    "Krom Praisanī Thōralėk": "Krom Praisanī Thōralēk",
    "yuk Phra Sīān": "yuk Phra Sī-ān",
    "Talātnat Ø.Tø.Kø.": "Talāt Ø.Tø.Kø.",
    "sātsanā Sōrōattoē": "sātsanā Sōrō-attoē",
    "sawatdiphāp khøng": "sawatdiphāp khøng chāt",
    "pāi jārājøn atcharia": "pāi jārājøn atchariya",
    "phāsā Angkrit samrap phāsā Angkrit samrap thurakit": "phāsā Angkrit samrap makkhuthēt",
    "Køsømø. (Khanakammakān Sitthi Manutsayachon haeng Chā": "Køsømø. (Khanakammakān Sitthi Manutsayachon haeng Chāt)",
    "phīseūa hāng khū phīseūa hāng khū sī tān mai": "phīseūa hāng khū sī ngoen",
    "khø sø søng phan": "khø sø søng phan sip et",
    "phū thī prasitthiphāp thīsut": "phū thī mī prasitthiphāp thīsut",
    "plā aēngloē lōfiidī": "plā aēngloē lōfi-idī",
    "priseum sāmlīem thraiøkmēn": "priseum sāmlīem thrai-økmēn",
    "witāmin aēntīsákhøbūtik": "witāmin aēntīsakhøbūtik",
    "phø.sø. 2549": "phø.sø. song phan ha røi si sip kāo",
    "sommāt / samamāt (*)": "sommāt",
    "[IKEA (TM)]": "",
    "Mǿmlūang": "Mǿmlūang (Mø.Lø.)",
    "pen ngai bāng ; ... pen ngai bāng": "pen ngai bāng",
    "nǿi si (... nǿi si)": "nǿi si",
    "øk kī mōng ; … øk kī mōng": "øk kī mōng",
    "thīnai (... thīnai)": "thīnai",
}

TONELESS_TO_THAI = {
    "Meūang Phetchaburī = Meūang Phetburī ; Amphoē Meūang Phetchaburī = Amphoē Meūang Phetburī":
    "เมืองเพชรบุรี ; อำเภอเมืองเพชรบุรี = อ.เมืองเพชรบุรี",

    "Nøng Yā Sai ; Amphoē Nøng Yā Sai":
    "หนองหญ้าไซ ; อำเภอหนองหญ้าไซ = อ.หนองหญ้าไซ",

    "Phra Phrom ; Amphoē Phra Phrom":
    "พระพรหม ; อำเภอพระพรหม = อ.พระพรหม",

    "dāo Phrǿksima Khon Khreung Mā":
    "ดาวพร็อกซิมาคนครึ่งม้า",

    "Samnakngān Khanakammakān Phatthanā Rabop Rātchakān (Kø.Phø.Rø.)":
    "สำนักงานคณะกรรมการพัฒนาระบบราชการ (ก.พ.ร.)",

    "theū wisāsa sadaēng khwām khithen":
    "ถือวิสาสะแสดงความคิดเห็น",

    "børikān dēlīwoērī": "บริการเดลิเวอรี่ = บริการเดลิเวอรี",

    "-khoēi": "เขย (-เขย)",
    "tingsati": "ติงสติ-",
    "Wīnas Willīem": "วีนัส วิลเลียมส์",
    "kotbat Øttāwā": "กฎบัตรออตตาวา",
    "mai mī soēphrai": "ไม่มีเซอร์ไพรส์",
    "chāo Sakǿt": "ชาวสก๊อต",
    "Fēnāndō": "เฟร์นานโด",
    "Karīeng Sako": "กะเหรี่ยงสะกอ",
    "keung haēng laēng": "กึ่งแห้งแล้ง",
    "kham athibā rāiwichā": "คำอธิบายรายวิชา",
    "kham athibāi rāiwichā": "คำอธิบายรายวิชา",
    "nikāi Hinayān": "นิกายหีนยาน",
    "nok theuttheū": "นกทึดทือ",
    "pam Saskō": "ปั๊มซัสโก้",
    "phra prātsanī": "พระปราษณี",
    "Prachai Līophairat": "ประชัย เลี่ยวไพรัตน์",
    "Rat Khwīnlaēn": "รัฐควีนส์แลนด์",
    "roēmton jāk sūn": "เริ่มต้นจากศูนย์",
    "wongjøn betset": "วงจรเบ็ดเสร็จ",
    "Nakhønrat Wātikan": "นครรัฐวาติกัน",
    "Køhø. (Krasūang Kalāhōm)": "กห. (กระทรวงกลาโหม)",
    "Møkhø. (Mahāwitthayālai Khøn Kaēn)": "มข. (มหาวิทยาลัยขอนแก่น)",
    "meung bā": "มึงบ้า",
    "Phiphitthaphan Rien": "พิพิธภัณฑ์เหรียญ",

}
THAI_TO_TONELESS = {
    "แม่ฟ้าหลวง ; อำเภอแม่ฟ้าหลวง = อ.แม่ฟ้าหลวง": "Maēfālūang ; Amphoē Maēfālūang",
    "กร่อม ; กร่อม ๆ = กร่อมๆ": "krǿm ; krǿm-krǿm",
    "ตุ ; ตุ ๆ = ตุๆ": "tu ; tu-tu",
    "อี๊ = อี๊ ! ; อี้": "ī ; ī",
    "โอย ; โอ๊ย ; โอ้ย": "oi ; oi ; oi",
    "บ ; บ่": "bø ; bø",
    "เอ ; เอ๊": "ē ; ē",
    "ฟี่ ; ฟี้": "fī ; fī",
    "ฮึย ; ฮึย ๆ = ฮึยๆ": "heuay ; heuay-heuay",
    "แจง ; แจ่ง": "jaēng ; jaēng",
    "จึง ; จึ่ง": "jeung ; jeung",
    "กำเบ้อ ; ก่ำเบ้อ": "kamboē ; kamboē",
    "แข่น ; แข้น": "khaēn ; khaēn",
    "กิก ; กิ๊ก": "kik ; kik",
    "โก่ ; โก้": "kō ; kō",
    "กวาน ; กว่าน": "kwān ; kwān",
    "มาห์ ; ม่าห์": "mā ; mā",
    "หมามุ่ย ; หมามุ้ย": "māmui ; māmui",
    "เอย ; เอ่ย": "oēi ; oēi",
    "ปีบ ; ปี๊บ": "pīp ; pīp",
    "ปราด ; ปร๊าด": "prāt ; prāt",
    "ซาง ; ซ่าง": "sāng ; sāng",
    "ซูด ; ซู้ด": "sūt ; sūt",
    "เทห์ ; เท่ห์": "thē ; thē",
    "แนะนำวิธีการใช้งาน": "naenam withīkān chaingān",
    "ค่าเฉลี่ยเลขคณิต": "khā chalīa lēkkhanit",
    "โรงพยาบาลช้าง": "rōngphayābān chāng",
    "กลุ่มดาวกิ้งก่า": "klum dāo Kingkā",
    "ยุ่งอยู่กับ": "yung yū kap",
    "ไม้พายเรือ": "māi phāi reūa",
    "แผนกวิชาการตลาด": "phanaēk wichākān talāt",
}
TONELESS_TO_VPHON = {
    "asōk Indīa": "_a_sōk -In-dīa",
    "atǿm khābǿn": r"_a-tǿm -khā\bǿn",
    "atǿm ǿksijēn": "_a-tǿm _ǿk_si-jēn",
    "āwut yutthōpakøn": "-ā¯wut ¯yut-thō_pa-køn",
    "børihān kānseūsān": "-bø¯ri/hān -kān_seū/sān",
    "būap ngū": "_būap -ngū",
    "dāokhrǿ khrae": "-dāo¯khrǿ ¯khrae",
    "Dāo sindrōm": "-Dāo -sindrōm",
    "dārāsāt fisik": "-dā-rā_sāt ¯fi_sik",
    "ēkkaphop meūt": r"_ēk_ka¯phop \meūt",
    "ēkkasān pokpit": "_ēk_ka/sān _pok_pit",
    "fakthøng sapākettī": r"¯fak-thøng _sa-pā_ket\tī",
    "fangchan ēkkaphan": r"-fang\chan _ēk_ka-phan",
    "hūarǿ kaēkoē": r"/hūa¯rǿ \kaē\koē",
    "jamnaēk yaēkyae": r"-jam\naēk \yaēk¯yae",
    "Jangwat Phetchabūn": "-Jang_wat ¯Phet¯cha-būn",
    "Jangwat Phitsanulōk": r"-Jang_wat ¯Phit_sa¯nu\lōk",
    "Jangwat Songkhlā": "-Jang_wat /Song/khlā",
    "Jangwat Sukhōthai": "-Jang_wat _Su/khō-thai",
    "Jangwat Suphanburī": "-Jang_wat _Su-phan_bu-rī",
    "Jangwat Udøn Thānī": "-Jang_wat _U-don -Thā-nī",
    "Jangwat Uthai Thānī": "-Jang_wat _U-thai -Thā-nī",
    "Jangwat Uttaradit": "-Jang_wat _Ut-ta¯ra_dit",
    "jathā sabīeng": "_jat/hā _sa-bīeng",
    "jatturat Latin": "_jat_tu_rat ¯La-tin",
    "jittrakam phūmithat": "_jit_tra-kam -phū¯mi¯that",
    "jøngtūa khreūangbin": r"-jøng/tūa \khreūang-bin",
    "kaēngsom marum": r"-kaēng\som ¯ma-rum",
    "kamyam lamsan": r"-kam-yam \lam/san",
    "kathā watthu": "_ka/thā ¯wat_thu",
    "khanakammakān chaphǿkit": "¯kha¯na-kam¯ma-kān _cha¯phǿ_kit",
    "khanom jan-ap": "_kha/nom -jan_ap",
    "khanom paēngjī": r"_kha/nom \paēng_jī",
    "khanom pankhlip": r"_kha/nom \pan_khlip",
    "khanom pansip": r"_kha/nom \pan_sip",
    "khanom pāthǿngkō": r"_kha/nom -pā\thǿng/kō",
    "khanom pong neng": "_kha/nom -pong _neng",
    "khāophat tāohū-yī": r"\khāo_phat \tāo\hū¯yī",
    "khomhēng rangkaē": "_khom/hēng -rang-kaē",
    "khopphloēng Ōlimpik": "¯khop-phloēng -Ō-lim_pik",
    "khreūangbaēp temyot": r"\khreūang_baēp -tem¯yot",
    "khreūangbin Aēbas": r"\khreūang-bin -Aē-bas",
    "khreūangbin prajanbān": r"\khreūang-bin _pra-jan-bān",
    "khreūangmāi jarājøn": r"\khreūang/māi _ja-rā-jøn",
    "khreūangmāi nakhalikhit": r"\khreūang/māi ¯na_kha¯li_khit",
    "khreūangmāi yattiphang": r"\khreūang/māi ¯yat_ti-phang",
    "khreung wongklom": r"\khreung -wong-klom",
    "khreung wongklom": r"\khreung -wong-klom",
    "khreung wongklom": r"\khreung -wong-klom",
    "khwāmkhit khamneung": "-khwām¯khit -kham-neung",
    "khwāmkhit lǿngløi": r"-khwām¯khit \lǿng-løi",
    "kindoē Nēthoēlaēn": r"-kin-doē -Nē\thoē-laēn",
    "klaiklīa khøphiphāt": r"_klai_klīa \khø¯phi\phāt",
    "køngrøi peūnyai": "-køng¯røi -peūn_yai",
    "kotmāi Rōman": "_kot/māi -Rō-man",
    "kotmāi sāthāranasuk": "_kot/māi /sā-thā ¯ra¯na_suk",
    "latthi Khongjeū": "¯lat¯thi /Khong¯jeū",
    "latthi phreuttikam": "¯lat¯thi ¯phreut_ti-kam",
    "Lek Nānā": "¯Lek -Nā-nā",
    "lūat døkmāiwai": r"\lūat _døk¯māi/wai",
    "madeūa uthumphøn": "¯ma_deūa _u-thum-phøn",
    "malaēng køk": "¯ma-laēng _køk",
    "malaēng kutjī": "¯ma-laēng _kut_jī",
    "malaēng kutjī": "¯ma-laēng _kut_jī",
    "malaēng kutjī": "¯ma-laēng _kut_jī",
    "malaēng nārī": "¯ma-laēng -nā-rī",
    "malet lahung": "¯ma¯let ¯la_hung",
    "malet thanyapheūt": r"¯ma¯let -than¯ya\pheūt",
    "māttrā tūasakot": r"\māt-trā -tūa_sa_kot",
    "mēt in": r"\mēt -in",
    "mēt in Chaina": r"\mēt -in -Chai¯na",
    "Nāi Kø": r"-Nāi \Kø",
    "ngū nākāk": r"-ngū \nā_kāk",
    "ngū pākkwāng": r"-ngū _pāk\kwāng",
    "ngū pīkaēo": r"-ngū _pī\kaēo",
    "ngū plǿng-øi": r"-ngū \plǿng\øi",
    "ngū sønnārāi": "-ngū /søn-nā-rāi",
    "nithētsāt mahābandit": r"¯ni\thēt_sāt ¯ma/hā-ban_dit",
    "niukhlīa fisik": "-niu-khlīa ¯fi_sik",
    "niyāi khopkhan": "¯ni-yāi _khop/khan",
    "nōt dontrī": "¯nōt -don-trī",
    "ongkān nitibukkhon": "-ong-kān ¯ni-ti_buk-khon",
    "Pākō Pākō": r"-Pā\kō -Pā\kō",
    "patikiriyā khāngkhīeng": r"_pa_ti_ki¯ri-yā \khāng-khīeng",
    "phaēnthī rūpthāi": r"/phaēn\thī \rūp_thāi",
    "phalang wangchā": "¯pha-lang -wang-chā",
    "phāpthāi phūmithat": r"\phāp_thāi -phū¯mi¯that",
    "phāsā Ākhā": "-phā/sā -Ā_khā",
    "phāsā Ēdā": "-phā/sā -Ē-dā",
    "phāsā Itālīen": "-phā/sā _I-tā-līen",
    "phāsā kaēkhat": r"-phā/sā \kaē_khat",
    "phāsā Khae": "-phā/sā ¯Khae",
    "phāsā phāthī": "-phā/sā -phā-thī",
    "phāsāsāt wannanā": "-phā/sā_sāt -wan¯na-nā",
    "phayāt saēmā": r"¯pha\yāt \saē¯mā",
    "phāyomyān nāwā": "¯pha-yōm-yān -nā-wā",
    "phīseūa ongkharak": r"/phī\seūa -ong¯kha¯rak",
    "phlēng pøp": "-phlēng _pøp",
    "phonlamāi chaē-im": r"/phon¯la¯māi \chaē_im",
    "Phrayā Mān": "¯Phra-yā -Mān",
    "phreuttikam phūbøriphōk": r"¯phreut_ti-kam \phū-bø¯ri\phōk",
    "phrōng sunak": "-phrōng _su¯nak",
    "phūmpanyā chāobān": r"-phūm-pan-yā -chāo\bān",
    "phūmpanyā pheūnbān": r"-phūm-pan-yā ¯pheūn\bān",
    "plā chaoheū": "-plā /chao¯heū",
    "plā kaēmcham": r"-plā \kaēm¯cham",
    "plā krasong": "-plā _kra/song",
    "plā lepmeūnāng": "-plā ¯lep-meū-nāng",
    "plā lot": "-plā ¯lot",
    "plā phae phaēndā": r"-plā ¯phae -phaēn\dā",
    "plā salāt": "-plā _sa_lāt",
    "pleūak hum": r"_pleūak \hum",
    "pleūak hum malet": r"_pleūak \hum ¯ma¯let",
    "plīen praden": "_plīen _pra-den",
    "plīen sakkarāt": "_plīen _sak_ka_rāt",
    "pløp pralōm": "_pløp _pra-lōm",
    "prachum phongsāwadān": "_pra-chum -phong/sā¯wa-dān",
    "prasomphan sukøn": "_pra/som-phan _su-køn",
    "rabīen khømūn": r"¯ra-bīen \khø-mūn",
    "rabop lamlīeng leūat": r"¯ra_bop -lam-līeng \leūat",
    "rabøp rāchāthippatai": "¯ra_bøp -rā-chā¯thip_pa-tai",
    "rabop satsūan": "¯ra_bop _sat_sūan",
    "rabop thōramāt": r"¯ra_bop -thō¯ra\māt",
    "rabop wajīwiphāk": r"¯ra_bop ¯wa-jī¯wi\phāk",
    "rabop wākkayasamphan": r"¯ra_bop \wāk_ka¯ya/sam-phan",
    "rabop wattajak": "¯ra_bop ¯wat_ta_jak",
    "rāchinī hin-øn": "-rā¯chi-nī /hin_øn",
    "raēt Sumāttrā": r"\raēt _Su\māt-trā",
    "rāidāi prachāchāt": r"-rāi\dāi _pra-chā\chāt",
    "rīek khāsīahāi": r"\rīek \khā\sīa/hāi",
    "rip sapsin": "¯rip ¯sap/sin",
    "rōng-ngān chǿkkōlaet": "-rōng-ngān ¯chǿk-kō¯laet",
    "rōngrīen datsandān": "-rōng-rīen _dat/san-dān",
    "røngthāo khīp": r"-røng¯thāo \khīp",
    "samnakngān athikānbodī": "/sam¯nak-ngān _a¯thi-kān-bo-dī",
    "sanōe yatti": "_sa/noē ¯yat_ti",
    "sānprakøp aninsī": "/sān _pra_køp _a-nin-sī",
    "sanyān anālǿk": "/san-yān _a-nā_lǿk",
    "sapphayākøn watthudip": "¯sap¯pha-yā-køn ¯wat_thu_dip",
    "sara a": "_sa_ra ¯a",
    "sara e": "_sa_ra ¯e",
    "sārakhadī chīwaprawat": "/sā¯ra¯kha-dī -chī¯wa_pra_wat",
    "sārānukrom ønlai": "/sā-rā¯nu-krom -øn-lai",
    "sārānukrom sērī": "/sā-rā¯nu-krom /sē-rī",
    "sara u": "_sa_ra _u",
    "satek thūnā": r"_sa¯tek -thū\nā",
    "sathāban khonkhwā": "_sa/thā-ban ¯khon¯khwā",
    "sathānī Sayām": "_sa/thā-nī _Sa/yām",
    "sathānthī patibattham": r"_sa/thān\thī _pa_ti_bat-tham",
    "satsūan matchim": "_sat_sūan ¯mat-chim",
    "sētthasāt mahaphāk": r"_sēt_tha_sāt ¯ma_ha\phāk",
    "sinlapa phāpphim": r"/sin¯la_pa \phāp-phim",
    "sitthi sēriphāp": r"_sit¯thi /sē-rī\phāp",
    "songkhrāmklāngmeūang Sapēn": "/song-khrām-klāng-meūang _Sa-pēn",
    "songsoēm thaksa": "_song/soēm ¯thak_sa",
    "sunak jønjat": "_su¯nak -jøn_jat",
    "surā mērai": "_su-rā -mē-rai",
    "takkataēn pāthangkā": r"¯tak_ka-taēn -pā-thang\kā",
    "talāt sērī": "_ta_lāt /sē-rī",
    "thabūangkān chamnanphisēt": "¯tha-būang-kān -cham-nan¯phi_sēt",
    "thamhai maomāi": r"-tham\hai -mao-māi",
    "thanthī thankhwan": "-than-thī -than-khwan",
    "Thērēsā Mē": "-Thē-rē-sā -Mē",
    "thīwī sāthārana": "-thī-wī /sā-thā ¯ra¯na",
    "thūangthī wājā": r"\thūang-thī -wā-jā",
    "trut songkrān": "_trut /song-krān",
    "tūalēk Ārabik": r"-tūa\lēk -Ā-ra_bik",
    "tūalēk patsēt": r"-tūa\lēk _pat_sēt",
    "wētchasāt feūnfū": r"\wēt¯cha_sāt ¯feūn-fū",
    "wipatsanā kammathān": "¯wi_pat_sa-nā -kam¯ma/thān",
    "witāmin Ē": "¯wi-tā-min -Ē",
    "witsawakam niukhlīa": "¯wit_sa¯wa-kam -niu-khlīa",
    "witsawakøn utsāhakān": "¯wit_sa¯wa-køn _ut/sā_ha-kān",
    "witthayālai āchīwaseuksā": "¯wit¯tha-yā-lai -ā-chī¯wa_seuk/sā",
    "yǿyoēi thākthāng": "¯yǿ¯yoēi _thāk/thāng",
    "yūa kilēt": "¯yūa _ki_lēt",
}

BAD_POS = {
    ('ชอบ', 'U'): 'n.',
    ('เนื้อตะเข้', 'U'): 'n.',
    ('เสียบ', 'A2 S'): 'v.',
    ('ติดกาว', 'I'): 'v.',
    ('ว่าวติดลม', 'X (loc.)'): 'n. exp.',
    ('สกุลสูง', '›'): 'n.',
    ('อะไรอื่น', ''): 'n.', # anything else
    ('จอบขุดดิน', ''): 'n.', # dig hole
    ('ไกด์นำเที่ยว', ''): 'n.', # tour guide
    ('ล้า', ''): 'adj.', # exhausted; tired; fatigued; worn out
    ('เลนส์กล้อง', ''): 'n.', # camera lens
    ('ปลาคาร์ปหญ้า', ''): 'n.', # grass carp
    ('รางวัลปลอบใจ', ''): 'n. exp.', # consolation prize
    ('สีเสียดเหนือ', ''): 'n.', # Acacia catechu
    ('อัลเบิร์ต ไอน์สไตน์', ''): 'n. prop.', # Albert Einstein
    ('มาเฟีย', 'h'): 'n.', # mafia
    ('สปิริต', 'm'): 'n.', # spirit
    ('เตรียมตัว', 'u'): 'v.', # prepare
    ('ตรุณะ', 'an'): 'n.', # boy
    ('ฯลฯ', 'symb.'): 'phrase',  # etc.
    ('สุขุมวิท', 'prop.'): 'n. prop.', # Sukhumvit
    ('มัน', 'pr. impers.'): 'pron.',  # it; we; they
    ('ฉัน', 'pr. pers. DOP'): 'pron.',  # me
    ('แม่', 'n. - pr.'): 'pron.',  # mum (term of endearment)
    ('ที่ดินให้เช่า', 'n. - pr.'): 'n.',  # None
    ('คุณลุง', 'n. exp. - pr.'): 'pron.',  # uncle
    ('คุณแม่', 'n. exp. - pr.'): 'pron.',  # mother
    ('คุณป้า', 'n. exp. - pr.'): 'pron.',  # aunt (elder sister of one's father or mother)
    ('คุณพ่อ', 'n. exp. - pr.'): 'pron.',  # father
    ('เนบิวลาเกลียว', 'n. exp. - pr.'): 'n. prop.', # Helix Nebula; Helix; NGC 7293; Caldwell 63
    ('พรเจริญ ; อำเภอพรเจริญ = อ.พรเจริญ', 'n. exp. - pr.'): 'n. prop.',  # Phon Charoen; Phon Charoen District
    ('โพนทราย ; อำเภอโพนทราย = อ.โพนทราย', 'n. exp. - pr.'): 'n. prop.',  # Phon Sai; Phon Sai District
    
}
NORMALIZED_POS = {
    "[TM]": "n. prop.",
    "abv.": "abbv.",
    "acron.": "abbv.",
    "adj. num.": "adj.",
    "adv. neg.": "adv.",
    "art.": "adj.",
    "aux.": "v.",
    "classif.": "classif.",
    "excl.": "interj.",
    "int": "interj.",
    "loc.": "phrase",
    "n. - num.": "num.",
    "n. - pr.": "n.",
    "part.": "particle",
    "pr. pers. (DOP)": "pron.",
    "pr. pers.": "pron.",
    "pr.": "pron.",
    "prov.": "phrase",
    "u": "n.",
    "x (loc.)": "phrase",
    "X": "<POS missing>",
    "x": "<POS missing>",
    "xp": "phrase",
}

SUFFIX_RE = re.compile(r"\s*\((-[^)]*?)\)\s*")
PARENS_RE = re.compile(r"\s*\(([^)]*?)\)\s*")
CORPORATE_RE = re.compile(r"\s*\((?:(?:องค์การ)?มหาชน|(?:Ongkān )?Mahāchon|(?:-Ong-kān )?¯Ma/hā-chon)\)\s*")
END_ELLIPSE_RE = re.compile(r"^\s*(?:\.{2,3}|…)\s*|\s*(?:\.{2,3}|…)\s*$")
MID_ELLIPSE_RE = re.compile(r"\s*(?:\.{2,3}|…)\s*")

DIPHTHONG_REPL = {
    "ūa": "ua",
    "Ūa": "Ua",
    "īa": "ia",
    "Īa": "Ia",
    "īe": "ia",
    "Īe": "Ia",
    "Iū": "iu",
    "iū": "iu",
}

tagset = {
    "poet": "poetic",
    "reg.": "dialectal",
    "rel.": "religious",
    "relig.": "religious",
    "vulg.": "vulgar",
    "pej.": "pejorative",
    "inf.": "informal",
    "fam.": "informal",
    "oral": "colloquial",
    "form.": "formal",
    "obsol.": "obsolete",
    "lit.": "literary",
    "neo.": "neologism",
    "fig.": "figurative",
    "idiom.": "idiomatic",
    "m.": "used_by_men",
    "f.": "used_by_women",
}

TAGS_TO_REMOVE = {
    "isan", "karen", "tai", "neua", "protoc", "adadj", "cl", "n", "exp", "aux", "anc", "r", "wiki"
}


def note_to_tags(note):
    note = note.strip("()")
    if "nickname" in note or "adjacent" in note:
        return None
    for tag, replacement in tagset.items():
        note = note.replace(tag, replacement)
        if tag == "reg." and "isan" in note:
            note = note.replace(
                "dialectal", "dialectal (Isan)")
    tags = re.findall(r'[\w_]+(?:\.)?\b(?: \(Isan\))?', note)
    tags = [tag for tag in tags if tag not in TAGS_TO_REMOVE]
    tags.sort()
    note = ", ".join(tags).replace("_", " ") if tags else None
    return note

def fix_colons_semicolons(s):
    return s.rstrip(":").rstrip(";").replace(":", ";").replace("; ;", ";")

def clean_string(s):
    s = s.replace("\xa0", " ").strip()
    s = DATA_FIXES.get(s, s)
    s = fix_colons_semicolons(s)
    s = re.sub(r"^…\s*", "-", s)
    s = re.sub(r"\s?= [^\*]+?\(?\*\)?", "", s)
    s = re.sub(r" \((?:Am\.|\?)\)$", "", s)
    s = re.sub(r"\((?:…|\.{3})\s*", "(-", s)
    s = CORPORATE_RE.sub("", s)
    return s

def parse_classifier(s):
    if not s.strip():
        return None
    classifiers = re.findall(r"[ก-๙]{2,}", s)
    result = " ; ".join([c for c in classifiers if c])
    if not result:
        return None
    return result


freq_src = get_corpus("ttc_freq.txt")
TTC_FREQS = {}
for item in freq_src:
    word, freq = item.split("\t")
    TTC_FREQS[word] = int(freq)


data = []
lao_data = []
isaan_data = []
with open(RAW_DIR / "VOLUBILIS Mundo(Volubilis).csv", "r") as f:
    reader = csv.reader(f)
    next(reader)
    for i, row in enumerate(reader, start=2):
        thai = clean_string(row[3])
        if thai in {"-ช", "---", "–ิ", "–ั"}:
            i += 1
            continue

        english = re.sub(r"\s*;", ";", row[4])
        english = english.replace("classif. :", "classif.:")
        english = re.sub(r"\s*:", ";", english)
        if english.startswith("Northern Ireland"):
            thai = "ไอร์แลนด์เหนือ"
        if english == "travel around the world" and not thai:
            thai = "เดินทางทั่วโลก"
        if "Thai–Lao Friendship Bridge" in english:
            i += 1
            continue
        if re.search(r"letter of the.* Thai alphabet", english):
            i += 1
            continue

        french = row[5]

        pos = row[6].split(", ")[-1]
        if thai != "ฯลฯ" and pos == "symb.":
            i += 1
            continue
        if (thai, pos) in BAD_POS:
            pos = BAD_POS[(thai, pos)]
        pos = re.sub(r"^\((.+)\)$", r"\1", pos)
        pos = PARENS_RE.sub("", pos)
        pos = NORMALIZED_POS.get(pos, pos)
        
        classifier = parse_classifier(row[10])
        
        toneless = clean_string(row[0]).replace("ASĪEN", "ĀSĪEN").replace("patibatikān", "patibatkān")
        vphon = clean_string(row[2]).replace(r"-A\SĪEN", r"-Ā\SĪEN")

        if english == "excessively" and thai == "จ๋อย":
            thai = "จ๋อย ; จ๋อย ๆ = จ๋อยๆ"
        if english == "shoe size" and thai == "ไซซ์ = ไซส์":
            thai = "ไซซ์รองเท้า = ไซส์รองเท้า"
        if toneless in TONELESS_TO_THAI:
            thai = TONELESS_TO_THAI[toneless]
        if thai in THAI_TO_TONELESS:
            toneless = THAI_TO_TONELESS[thai]
        if toneless == "yāng- (+n.)":
            toneless = "yāng-"
            english += " (before a noun)"
        if toneless == "yāng- (+adj.)":
            toneless = "yāng-"
            english += " (before an adjective)"

        if m := re.match(r"\[classif.; (.+)\]", english):
            pos = "classif."
            english = english.replace("classif; ", "for ")
        if m := re.search(r"\s*\(prefix\)", english):
            pos = "pref."
            english = english[:m.start(0)]

        note = row[7] or None
        if note and "obsol." in note:
            i += 1
            continue
        if note == "obj., anim.":
            english += " [animate object pronoun]"
        note = note_to_tags(note)

        if thai == "บันดาลใจ" and toneless == "raēng cheūay":
            i += 1
            continue # erroneous row
        if toneless == "wēthanā" and pos == "v.":
            i += 1
            continue  # Wrong pronunciation - subtle case
        
        for sub_entry_thai, sub_entry_toneless, sub_entry_vphon in zip_longest(
                thai.split(";"), toneless.split(";"), vphon.split(";"), fillvalue=""):
            
            needs_check_romanization = False
            suffix = None
            see_also = {}

            sub_entry_thai = END_ELLIPSE_RE.sub("", sub_entry_thai.strip())
            if suffix_m := SUFFIX_RE.search(sub_entry_thai):
                suffix = suffix_m.group(1)
                sub_entry_thai = sub_entry_thai[:suffix_m.start(0)]    
            if parens := PARENS_RE.search(sub_entry_thai):
                see_also["thai"] = parens.group(1)
                sub_entry_thai = sub_entry_thai[:parens.start(0)]
            sub_entry_thai = END_ELLIPSE_RE.sub("", sub_entry_thai.strip())
            sub_entry_thai = MID_ELLIPSE_RE.sub("…", sub_entry_thai)
            sub_entry_thai = sub_entry_thai.replace("[", "").replace("]", "")

            sub_entry_toneless = END_ELLIPSE_RE.sub("", sub_entry_toneless.strip())
            if pos == "n.":
                sub_entry_toneless = sub_entry_toneless.lower()
            if parens := PARENS_RE.search(sub_entry_toneless):
                see_also["toneless"] = parens.group(1)
                sub_entry_toneless = sub_entry_toneless[:parens.start(0)]
            sub_entry_toneless = END_ELLIPSE_RE.sub("", sub_entry_toneless.strip())
            sub_entry_toneless = MID_ELLIPSE_RE.sub(" … ", sub_entry_toneless)
            sub_entry_toneless = sub_entry_toneless.replace("[", "").replace("]", "")
            
            sub_entry_vphon = END_ELLIPSE_RE.sub("", sub_entry_vphon.strip())
            if pos == "n.":
                sub_entry_vphon = sub_entry_vphon.lower()
            if parens := PARENS_RE.search(sub_entry_vphon):
                see_also["vphon"] = parens.group(1)
                sub_entry_vphon = sub_entry_vphon[:parens.start(0)]
            sub_entry_vphon = END_ELLIPSE_RE.sub("", sub_entry_vphon.strip())
            sub_entry_vphon = MID_ELLIPSE_RE.sub(" … ", sub_entry_vphon)
            sub_entry_vphon = sub_entry_vphon.replace("[", "").replace("]", "")
    
            # = signs in the fields indicate equally valid variants in spelling and pronunciation
            # However due to the peculiarities of the Volubilis romanization, sometimes there are
            # unnecessary distinctions
            if "=" in sub_entry_thai:
                thai_variants = [v.strip() for v in sub_entry_thai.split('=') if 
                                 v.strip() and not "*" in v]
            else:
                thai_variants = [sub_entry_thai]
            toneless_variants, vphon_variants = [], []

            if "vowel mark" in english:
                see_also = {}

            if pos == "pref." and not thai_variants[0].endswith("-"):
                thai_variants[0] += "-"
            
            if sub_entry_toneless and "=" in sub_entry_toneless:
                for v in sub_entry_toneless.split('='):
                    v = v.strip()
                    for patt, repl in DIPHTHONG_REPL.items():
                        v = re.sub(patt, repl, v)
                    if v and v not in toneless_variants:
                        toneless_variants.append(v)
                sub_entry_toneless = " = ".join(toneless_variants)
            
            if sub_entry_vphon and "=" in sub_entry_vphon:
                for v in sub_entry_vphon.split('='):
                    v = v.strip()
                    for patt, repl in DIPHTHONG_REPL.items():
                        v = re.sub(patt, repl, v)
                    if v and v not in vphon_variants:
                        vphon_variants.append(v)
                sub_entry_vphon = " = ".join(vphon_variants)

            if sub_entry_toneless in TONELESS_TO_VPHON:
                sub_entry_vphon = TONELESS_TO_VPHON[sub_entry_toneless]
            else:
                plain_vphons = set(make_plain(v) for v in sub_entry_vphon.split(" = "))
                plain_tonelesses = set(make_plain(v) for v in sub_entry_toneless.split(" = "))
                if all(" " not in t for t in plain_tonelesses) and any(" " in v for v in plain_vphons):
                    plain_vphons = set(make_plain(v).replace(" ", "") for v in sub_entry_vphon.split(" "))
                if not plain_vphons & plain_tonelesses:
                    needs_check_romanization = True
            
            if thai_variants[0].endswith("-"):
                thai_variants.append(thai_variants[0][:-1])
            # Actually, these should be swapped, but let's do this in SQL below
            if suffix and len(suffix) > 2:
                thai_variants.append(suffix)
            # Collapse whitespace of org names
            if pos not in {'org.', 'n. prop.'}:
                pass
            elif (spaceless := re.sub(r"(?<=[ก-๙])\s(?=[ก-๙])", "", thai_variants[0])) and spaceless not in thai_variants:
                thai_variants.append(spaceless)

            vphon_aua = None
            if sub_entry_vphon and not needs_check_romanization:
                vphon_aua = romanize_from_volubilis(
                    sub_entry_vphon, thai_variants[0])
                if pos == "suff." and not vphon_aua.startswith("-"):
                    vphon_aua = "-" + vphon_aua

            data.append([i,
                         thai_variants[0], 
                         " = ".join(thai_variants[1:]) if len(thai_variants) > 1 else None,
                         json.dumps(see_also, ensure_ascii=False) if see_also else None, 
                         sub_entry_toneless or None, 
                         sub_entry_vphon or None, 
                         vphon_aua,
                         english or None,
                         None if english else french or None,
                         pos, 
                         classifier,
                         TTC_FREQS.get(thai_variants[0], None),
                         note,
                         'volubilis' if vphon_aua else None,
                         needs_check_romanization])
            
        lao = row[27] or None
        lao_toneless = row[28] or None
        if lao:
            lao_data.append([i, lao, lao_toneless, english, french, pos, note])

        isaan = row[29] or None
        isaan_toneless = row[30] or None
        if isaan:
            isaan_data.append([i, isaan, isaan_toneless, english, french, pos, note])

# Make the actual DB that will function as a workspace from which to export the final JSON
with sqlite3.connect(DB_PATH) as conn:
    c = conn.cursor()
    c.execute("DROP TABLE IF EXISTS volubilis")
    c.execute("""
        CREATE TABLE IF NOT EXISTS volubilis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            csv_row INTEGER NOT NULL,
            thai TEXT NOT NULL,
            variants TEXT,
            see_also JSON,
            toneless TEXT,
            vphon TEXT,
            ipa TEXT,
            roman TEXT, 
            english TEXT, 
            french TEXT,
            pos TEXT, 
            classifier TEXT,
            freq INTEGER,
            note TEXT,  
            pron_src TEXT,
            needs_check_romanization BOOLEAN,
            flag_reason TEXT
        )
    """)
    c.executemany("""
        INSERT INTO volubilis (csv_row, thai, variants, see_also, toneless, vphon, roman, english, french, pos, classifier, freq, note, pron_src, needs_check_romanization)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, data)
    conn.commit()

    # Swapping the variant in the case of suffixes
    c.execute("""
        UPDATE volubilis SET variants = thai, thai = variants WHERE variants LIKE '-%'
    """)
    conn.commit()
    
    print("Done!")
    print("Validating data...")

    c.execute("""
        SELECT COUNT(*) FROM volubilis
    """)
    total_rows = c.fetchone()[0]
    c.execute("""
        SELECT COUNT(distinct csv_row) FROM volubilis
    """)
    csv_rows = c.fetchone()[0]
    c.execute("""
        SELECT COUNT(distinct thai) FROM volubilis WHERE thai <> ''
    """)
    headword_count = c.fetchone()[0]
    c.execute("""
        SELECT COUNT(*) FROM volubilis WHERE thai = ''
    """)
    blank_thai_count = c.fetchone()[0]
    c.execute("""
        SELECT COUNT(*) FROM volubilis WHERE toneless = '' OR toneless IS NULL
    """)
    blank_toneless_count = c.fetchone()[0]
    c.execute("""
        SELECT COUNT(*) FROM volubilis WHERE needs_check_romanization = 1
    """)
    needs_check_count = c.fetchone()[0]

    print(f"There are {total_rows} rows in the table, compared to {csv_rows} rows in the source CSV.")
    print(f"There are {headword_count} unique headwords.")
    
    print(f"There are {blank_thai_count} rows without a Thai headword. (This number should be 0.)")
    print(f"There are {blank_toneless_count} rows without a toneless romanization. (This number should be 0.)")
    
    print(f"There are {needs_check_count} rows without a complete AUA-style romanization.")

    print(f"Creating tables for Lao and Isaan words...")

    c.execute("DROP TABLE IF EXISTS volubilis_lao")
    c.execute("""
        CREATE TABLE IF NOT EXISTS volubilis_lao (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            csv_row INTEGER NOT NULL,
            lao TEXT NOT NULL,
            toneless TEXT,
            english TEXT, 
            french TEXT, 
            pos TEXT, 
            note TEXT
        )
    """)
    c.executemany("""
        INSERT INTO volubilis_lao (csv_row, lao, toneless, english, french, pos, note)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, lao_data)
    conn.commit()

    c.execute("DROP TABLE IF EXISTS volubilis_isaan")
    c.execute("""
        CREATE TABLE IF NOT EXISTS volubilis_isaan (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            csv_row INTEGER NOT NULL,
            isaan TEXT NOT NULL,
            toneless TEXT,
            english TEXT, 
            french TEXT, 
            pos TEXT, 
            note TEXT
        )
    """)
    c.executemany("""
        INSERT INTO volubilis_isaan (csv_row, isaan, toneless, english, french, pos, note)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, isaan_data)
    conn.commit()

    print("Done!")