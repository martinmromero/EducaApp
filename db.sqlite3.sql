BEGIN TRANSACTION;
CREATE TABLE IF NOT EXISTS "auth_group" (
	"id"	integer NOT NULL,
	"name"	varchar(150) NOT NULL UNIQUE,
	PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "auth_group_permissions" (
	"id"	integer NOT NULL,
	"group_id"	integer NOT NULL,
	"permission_id"	integer NOT NULL,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("group_id") REFERENCES "auth_group"("id") DEFERRABLE INITIALLY DEFERRED,
	FOREIGN KEY("permission_id") REFERENCES "auth_permission"("id") DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE IF NOT EXISTS "auth_permission" (
	"id"	integer NOT NULL,
	"content_type_id"	integer NOT NULL,
	"codename"	varchar(100) NOT NULL,
	"name"	varchar(255) NOT NULL,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("content_type_id") REFERENCES "django_content_type"("id") DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE IF NOT EXISTS "auth_user" (
	"id"	integer NOT NULL,
	"password"	varchar(128) NOT NULL,
	"last_login"	datetime,
	"is_superuser"	bool NOT NULL,
	"username"	varchar(150) NOT NULL UNIQUE,
	"last_name"	varchar(150) NOT NULL,
	"email"	varchar(254) NOT NULL,
	"is_staff"	bool NOT NULL,
	"is_active"	bool NOT NULL,
	"date_joined"	datetime NOT NULL,
	"first_name"	varchar(150) NOT NULL,
	PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "auth_user_groups" (
	"id"	integer NOT NULL,
	"user_id"	integer NOT NULL,
	"group_id"	integer NOT NULL,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("group_id") REFERENCES "auth_group"("id") DEFERRABLE INITIALLY DEFERRED,
	FOREIGN KEY("user_id") REFERENCES "auth_user"("id") DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE IF NOT EXISTS "auth_user_user_permissions" (
	"id"	integer NOT NULL,
	"user_id"	integer NOT NULL,
	"permission_id"	integer NOT NULL,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("permission_id") REFERENCES "auth_permission"("id") DEFERRABLE INITIALLY DEFERRED,
	FOREIGN KEY("user_id") REFERENCES "auth_user"("id") DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE IF NOT EXISTS "django_admin_log" (
	"id"	integer NOT NULL,
	"object_id"	text,
	"object_repr"	varchar(200) NOT NULL,
	"action_flag"	smallint unsigned NOT NULL CHECK("action_flag" >= 0),
	"change_message"	text NOT NULL,
	"content_type_id"	integer,
	"user_id"	integer NOT NULL,
	"action_time"	datetime NOT NULL,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("content_type_id") REFERENCES "django_content_type"("id") DEFERRABLE INITIALLY DEFERRED,
	FOREIGN KEY("user_id") REFERENCES "auth_user"("id") DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE IF NOT EXISTS "django_content_type" (
	"id"	integer NOT NULL,
	"app_label"	varchar(100) NOT NULL,
	"model"	varchar(100) NOT NULL,
	PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "django_migrations" (
	"id"	integer NOT NULL,
	"app"	varchar(255) NOT NULL,
	"name"	varchar(255) NOT NULL,
	"applied"	datetime NOT NULL,
	PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "django_session" (
	"session_key"	varchar(40) NOT NULL,
	"session_data"	text NOT NULL,
	"expire_date"	datetime NOT NULL,
	PRIMARY KEY("session_key")
);
CREATE TABLE IF NOT EXISTS "material_exam" (
	"id"	integer NOT NULL,
	"title"	varchar(255) NOT NULL,
	"topics"	text NOT NULL,
	"created_at"	datetime NOT NULL,
	"created_by_id"	integer,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("created_by_id") REFERENCES "auth_user"("id") DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE IF NOT EXISTS "material_exam_questions" (
	"id"	integer NOT NULL,
	"exam_id"	bigint NOT NULL,
	"question_id"	bigint NOT NULL,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("exam_id") REFERENCES "material_exam"("id") DEFERRABLE INITIALLY DEFERRED,
	FOREIGN KEY("question_id") REFERENCES "material_question"("id") DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE IF NOT EXISTS "material_examtemplate" (
	"id"	integer NOT NULL,
	"institution_logo"	varchar(100),
	"institution_name"	varchar(255) NOT NULL,
	"career_name"	varchar(255) NOT NULL,
	"subject_name"	varchar(255) NOT NULL,
	"professor_name"	varchar(255) NOT NULL,
	"year"	integer NOT NULL,
	"exam_type"	varchar(10) NOT NULL,
	"exam_mode"	varchar(10) NOT NULL,
	"notes_and_recommendations"	text NOT NULL,
	"topics_to_evaluate"	text,
	"created_at"	datetime NOT NULL,
	"created_by_id"	integer,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("created_by_id") REFERENCES "auth_user"("id") DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE IF NOT EXISTS "material_material" (
	"id"	integer NOT NULL,
	"file"	varchar(100) NOT NULL,
	"uploaded_at"	datetime NOT NULL,
	"title"	varchar(255) NOT NULL,
	"uploaded_by_id"	integer,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("uploaded_by_id") REFERENCES "auth_user"("id") DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE IF NOT EXISTS "material_profile" (
	"id"	integer NOT NULL,
	"role"	varchar(10) NOT NULL,
	"user_id"	integer NOT NULL UNIQUE,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("user_id") REFERENCES "auth_user"("id") DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE IF NOT EXISTS "material_question" (
	"id"	integer NOT NULL,
	"question_text"	text NOT NULL,
	"answer_text"	text NOT NULL,
	"topic"	varchar(255) NOT NULL,
	"subtopic"	varchar(255) NOT NULL,
	"source_page"	integer NOT NULL,
	"material_id"	bigint NOT NULL,
	"chapter"	text,
	"subject_id"	INTEGER,
	"user_id"	INTEGER NOT NULL,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("material_id") REFERENCES "material_material"("id") DEFERRABLE INITIALLY DEFERRED,
	FOREIGN KEY("subject_id") REFERENCES "material_subjects"("id"),
	FOREIGN KEY("user_id") REFERENCES "auth_user"("id")
);
CREATE TABLE IF NOT EXISTS "material_subjects" (
	"id"	integer NOT NULL,
	"name"	varchar(100) NOT NULL UNIQUE,
	"Nombre"	varchar(100) NOT NULL,
	PRIMARY KEY("id" AUTOINCREMENT)
);
INSERT INTO "auth_permission" VALUES (1,1,'add_logentry','Can add log entry');
INSERT INTO "auth_permission" VALUES (2,1,'change_logentry','Can change log entry');
INSERT INTO "auth_permission" VALUES (3,1,'delete_logentry','Can delete log entry');
INSERT INTO "auth_permission" VALUES (4,1,'view_logentry','Can view log entry');
INSERT INTO "auth_permission" VALUES (5,2,'add_permission','Can add permission');
INSERT INTO "auth_permission" VALUES (6,2,'change_permission','Can change permission');
INSERT INTO "auth_permission" VALUES (7,2,'delete_permission','Can delete permission');
INSERT INTO "auth_permission" VALUES (8,2,'view_permission','Can view permission');
INSERT INTO "auth_permission" VALUES (9,3,'add_group','Can add group');
INSERT INTO "auth_permission" VALUES (10,3,'change_group','Can change group');
INSERT INTO "auth_permission" VALUES (11,3,'delete_group','Can delete group');
INSERT INTO "auth_permission" VALUES (12,3,'view_group','Can view group');
INSERT INTO "auth_permission" VALUES (13,4,'add_user','Can add user');
INSERT INTO "auth_permission" VALUES (14,4,'change_user','Can change user');
INSERT INTO "auth_permission" VALUES (15,4,'delete_user','Can delete user');
INSERT INTO "auth_permission" VALUES (16,4,'view_user','Can view user');
INSERT INTO "auth_permission" VALUES (17,5,'add_contenttype','Can add content type');
INSERT INTO "auth_permission" VALUES (18,5,'change_contenttype','Can change content type');
INSERT INTO "auth_permission" VALUES (19,5,'delete_contenttype','Can delete content type');
INSERT INTO "auth_permission" VALUES (20,5,'view_contenttype','Can view content type');
INSERT INTO "auth_permission" VALUES (21,6,'add_session','Can add session');
INSERT INTO "auth_permission" VALUES (22,6,'change_session','Can change session');
INSERT INTO "auth_permission" VALUES (23,6,'delete_session','Can delete session');
INSERT INTO "auth_permission" VALUES (24,6,'view_session','Can view session');
INSERT INTO "auth_permission" VALUES (25,7,'add_material','Can add material');
INSERT INTO "auth_permission" VALUES (26,7,'change_material','Can change material');
INSERT INTO "auth_permission" VALUES (27,7,'delete_material','Can delete material');
INSERT INTO "auth_permission" VALUES (28,7,'view_material','Can view material');
INSERT INTO "auth_permission" VALUES (29,8,'add_question','Can add question');
INSERT INTO "auth_permission" VALUES (30,8,'change_question','Can change question');
INSERT INTO "auth_permission" VALUES (31,8,'delete_question','Can delete question');
INSERT INTO "auth_permission" VALUES (32,8,'view_question','Can view question');
INSERT INTO "auth_permission" VALUES (33,9,'add_exam','Can add exam');
INSERT INTO "auth_permission" VALUES (34,9,'change_exam','Can change exam');
INSERT INTO "auth_permission" VALUES (35,9,'delete_exam','Can delete exam');
INSERT INTO "auth_permission" VALUES (36,9,'view_exam','Can view exam');
INSERT INTO "auth_permission" VALUES (37,10,'add_profile','Can add profile');
INSERT INTO "auth_permission" VALUES (38,10,'change_profile','Can change profile');
INSERT INTO "auth_permission" VALUES (39,10,'delete_profile','Can delete profile');
INSERT INTO "auth_permission" VALUES (40,10,'view_profile','Can view profile');
INSERT INTO "auth_permission" VALUES (41,11,'add_examtemplate','Can add exam template');
INSERT INTO "auth_permission" VALUES (42,11,'change_examtemplate','Can change exam template');
INSERT INTO "auth_permission" VALUES (43,11,'delete_examtemplate','Can delete exam template');
INSERT INTO "auth_permission" VALUES (44,11,'view_examtemplate','Can view exam template');
INSERT INTO "auth_permission" VALUES (45,12,'add_subject','Can add Subject');
INSERT INTO "auth_permission" VALUES (46,12,'change_subject','Can change Subject');
INSERT INTO "auth_permission" VALUES (47,12,'delete_subject','Can delete Subject');
INSERT INTO "auth_permission" VALUES (48,12,'view_subject','Can view Subject');
INSERT INTO "auth_permission" VALUES (49,13,'add_subtopic','Can add subtopic');
INSERT INTO "auth_permission" VALUES (50,13,'change_subtopic','Can change subtopic');
INSERT INTO "auth_permission" VALUES (51,13,'delete_subtopic','Can delete subtopic');
INSERT INTO "auth_permission" VALUES (52,13,'view_subtopic','Can view subtopic');
INSERT INTO "auth_permission" VALUES (53,14,'add_topic','Can add topic');
INSERT INTO "auth_permission" VALUES (54,14,'change_topic','Can change topic');
INSERT INTO "auth_permission" VALUES (55,14,'delete_topic','Can delete topic');
INSERT INTO "auth_permission" VALUES (56,14,'view_topic','Can view topic');
INSERT INTO "auth_user" VALUES (3,'pbkdf2_sha256$720000$museAOJCrz0ccXcSrr4DU0$puqfdcSqBG9vm0EAA7pXwbCnImDrsBw3yxEUYHFqy7U=','2025-03-25 03:08:31.397541',0,'pepe','mujica','pepechorro@gma.crttom',1,1,'2025-02-12 21:00:39.228926','joselitx');
INSERT INTO "auth_user" VALUES (4,'pbkdf2_sha256$600000$S7rqmxQLzbE44rD7gIVLhf$JcPgOaAHzgatxQLHukaEk0p6haSo6Q/vRe7OlITSNwo=','2025-04-05 23:46:20.856935',1,'romi','dfgdsf','tintiti@ho.com',1,1,'2025-02-14 00:25:02.685941','saadf');
INSERT INTO "auth_user" VALUES (5,'pbkdf2_sha256$720000$Y3koXDZUThYi8VUqWhACsY$dVx3R/lymqAZbyB7fqldjDW8GyN7NMIbij8Mq0hkbRE=','2025-03-25 04:22:21.985423',1,'martin','boletal','martin@example.com',1,1,'2025-02-16 00:13:32.350337','pibes333');
INSERT INTO "django_content_type" VALUES (1,'admin','logentry');
INSERT INTO "django_content_type" VALUES (2,'auth','permission');
INSERT INTO "django_content_type" VALUES (3,'auth','group');
INSERT INTO "django_content_type" VALUES (4,'auth','user');
INSERT INTO "django_content_type" VALUES (5,'contenttypes','contenttype');
INSERT INTO "django_content_type" VALUES (6,'sessions','session');
INSERT INTO "django_content_type" VALUES (7,'material','material');
INSERT INTO "django_content_type" VALUES (8,'material','question');
INSERT INTO "django_content_type" VALUES (9,'material','exam');
INSERT INTO "django_content_type" VALUES (10,'material','profile');
INSERT INTO "django_content_type" VALUES (11,'material','examtemplate');
INSERT INTO "django_content_type" VALUES (12,'material','subject');
INSERT INTO "django_content_type" VALUES (13,'material','subtopic');
INSERT INTO "django_content_type" VALUES (14,'material','topic');
INSERT INTO "django_migrations" VALUES (1,'contenttypes','0001_initial','2025-02-12 03:32:06.889822');
INSERT INTO "django_migrations" VALUES (2,'auth','0001_initial','2025-02-12 03:32:06.918971');
INSERT INTO "django_migrations" VALUES (3,'admin','0001_initial','2025-02-12 03:32:06.941981');
INSERT INTO "django_migrations" VALUES (4,'admin','0002_logentry_remove_auto_add','2025-02-12 03:32:06.960574');
INSERT INTO "django_migrations" VALUES (5,'admin','0003_logentry_add_action_flag_choices','2025-02-12 03:32:06.974090');
INSERT INTO "django_migrations" VALUES (6,'contenttypes','0002_remove_content_type_name','2025-02-12 03:32:07.004318');
INSERT INTO "django_migrations" VALUES (7,'auth','0002_alter_permission_name_max_length','2025-02-12 03:32:07.028308');
INSERT INTO "django_migrations" VALUES (8,'auth','0003_alter_user_email_max_length','2025-02-12 03:32:07.045880');
INSERT INTO "django_migrations" VALUES (9,'auth','0004_alter_user_username_opts','2025-02-12 03:32:07.058766');
INSERT INTO "django_migrations" VALUES (10,'auth','0005_alter_user_last_login_null','2025-02-12 03:32:07.077203');
INSERT INTO "django_migrations" VALUES (11,'auth','0006_require_contenttypes_0002','2025-02-12 03:32:07.081243');
INSERT INTO "django_migrations" VALUES (12,'auth','0007_alter_validators_add_error_messages','2025-02-12 03:32:07.096111');
INSERT INTO "django_migrations" VALUES (13,'auth','0008_alter_user_username_max_length','2025-02-12 03:32:07.114404');
INSERT INTO "django_migrations" VALUES (14,'auth','0009_alter_user_last_name_max_length','2025-02-12 03:32:07.137890');
INSERT INTO "django_migrations" VALUES (15,'auth','0010_alter_group_name_max_length','2025-02-12 03:32:07.155356');
INSERT INTO "django_migrations" VALUES (16,'auth','0011_update_proxy_permissions','2025-02-12 03:32:07.165985');
INSERT INTO "django_migrations" VALUES (17,'auth','0012_alter_user_first_name_max_length','2025-02-12 03:32:07.188788');
INSERT INTO "django_migrations" VALUES (18,'material','0001_initial','2025-02-12 03:32:07.213677');
INSERT INTO "django_migrations" VALUES (19,'sessions','0001_initial','2025-02-12 03:32:07.228491');
INSERT INTO "django_migrations" VALUES (20,'material','0002_alter_material_title','2025-02-14 01:50:51.017331');
INSERT INTO "django_migrations" VALUES (21,'material','0003_exam_created_by_alter_material_title','2025-02-14 15:08:23.921054');
INSERT INTO "django_migrations" VALUES (22,'material','0004_material_uploaded_by','2025-02-14 16:45:36.483214');
INSERT INTO "django_migrations" VALUES (23,'material','0005_profile','2025-02-14 22:39:32.697337');
INSERT INTO "django_migrations" VALUES (24,'material','0006_question_chapter','2025-02-15 22:56:40.767940');
INSERT INTO "django_migrations" VALUES (25,'material','0007_examtemplate','2025-03-15 16:02:55.601911');
INSERT INTO "django_migrations" VALUES (26,'material','0002_add_nombre_field','2025-03-25 01:00:03.547842');
INSERT INTO "django_session" VALUES ('ydvh8pkm86sfd04awc9q7yivbsuerz1v','e30:1tiH29:5YY6ZcJopUJS9Q9wZ44EW9zm9Xg-o9baMWkmkJT4cUM','2025-02-26 18:00:25.325652');
INSERT INTO "django_session" VALUES ('t6voh7ahgddmj5skljipji5nczyk6298','e30:1tj4N0:0xWzecRbzOt8JGfPS2Q97rKtwCx-q11PADlD0XzOJt4','2025-02-28 22:41:14.152833');
INSERT INTO "django_session" VALUES ('4nuidh3iv8bv0pukgdw0nymcjncdij3p','e30:1tj4Nc:MCgmSEK2_QMQRLa9KffXyuv_L7OYJkQe2Sidg3vC7SQ','2025-02-28 22:41:52.724659');
INSERT INTO "django_session" VALUES ('8ejz959ywow1swm0zo040qjohhe81wpg','.eJztXGFvG7kR_StEUKAtIG0lO4qtfClkxblLajuBnbu01ysCapeSaO-Se-SuHLnof--bIVdaJ3dZX9QGMKBDcF6tdsnh8HHmzXCofz_5IOtq-aH2yn3Q2ZPnT0ZPeu17M5neKENfZNfSLGySWlM5PUvokSR-65Nzm6n8JD57r4Gl9Eu8fTAejrKDg-PRYJypw7k6Gg6P5NN0ePhMydH8OBsfDgbD-XCGqyH-Gx3LNBuMByqbPz3C9wdodKGMcrJS2YdfauUrbY1_8vyfT36uB4PZ_IUSv9R0qcaiwlNS4BElUlnyzayqc_tXNHKpfElvy-di4jUeMXgqU2JVq9yqlTbiYlGvlRFeLeUsvCvFQhqZWVEb8dK6TJx-LHPrlEvEz_XBYJheWIFG8UDqlHK55btZT2T62sb2ehBPQbCZvIZoRkyhRm3Qu8zRvYcEw_H4KBEvncrEuc5z5Xqi1LmtLIl3NDr65K0eJCS5SMT5IYnWSIWRK1FoX-DNOICERz5XTplUY-jTtlrEEN_i31crcnpxAVgU4hZii7mSVe2U0JeqtK6COOUSg_ACqpXiVqmbfC3eOblSubgysvT41mMgNOJ1It7mSkJ8X88KXYm1rZ2YoRcRHrNzceLknUY31gmjPlbcYiJ-1B6PR0H-Epvn79-rzEC_cs2vSNy8bXqj5nwjwpdVdLCjiiZYC5g6zElPOFvJVId5Ay68xP25TFu3SmezOq30SmcSMCosLreviLVI6xxKloSMXArrgAN913pCYgJkvqgN9E7P4M9KOi1nufIEROFUqVxaA_6AFZpo9WhNIs6kyLE4uAMaQOv1noCGrVjpAo3idbz8cz2fDYYLEmiYHPXwRi4hEslJeMWypYtUlQQDvF3mOsVyQlNFnS4tTyuJmNaS5PPWZHoeVJlqukNSrGReS_flWTrcA7kLyE93VNEZFBDNWAZjw3MzGgnJyBsyJCRcgSSziokUkN6rtILEeLCQa1zASKa6ACxg2hQ_UQCLZF9zObN9J3MGID_cGOAI4saA4uMpxAGGxA9G0581FGIFg81EhFfaSedpIQBZBDonjgZQ3Frh9pe1NNoDqQtIz3ZU0akRwaHDk5EZIej4qs40Lmi4KiBKwr7URgrpLYTYWrjSYniwini3cmwFAZMMJgdXn1lUBhbjalpLw0BrG0SvYteS2nX4XEoHcPXajW1ta12QA246hrgwnnPlte0bzbYSxg6aLdCqWalrlZL3Z7w7GaxvBkegDWhBMKBoQTksFlwAw01rpsNrH-0x2oXR4x1VdIJB-ehkMankIcn25NBKRq6yhj0dbpBKZoiA0_gqnlmQSJ2TG1eky0rlMIbBzUX0K0_WDiDUipioBrho8vFAwXINgScNU8e4guPVBU0Q2Vf2lEKWlQZ2hanD82MH58pOunTUVAPblXIzrDVoGAuJlgqGRRxAlS1omwy2uLBYGF9W7HiPvS7sDQe7GkgODFRRRnzZxgniFoacBTs5lyu44VQReSLL5olrOTjmEniFdWnjj6YXg-QObIL4J_TdY6MHQ4V2yeZZH-IOvLDS0csbdAF9SWrw5NVZbNAH4FD7vExW2gPb95goBMEndumW7Zy22cZKouMZtd4I2c_CcsOEwfxFigCOmjU8wGCBBLZJDJhk6JiEfWjTDdRdYxsAlYyjTvV20tI8Gi-dguSRXfR6RZjLF8BonSrM8hocjZw0vRXiFDj6QpJVZC_pa7dgD-mavojKSYoptgSSAgtQvRacCXIgB_DsQn3kUCNY4saAe7THGDpQ12x3aTnBCL9VjvlotMu0UsiIkrHlvjDvnsJsPF_n3ooCcRnAUC2BSmIoYTAR9x0q3wcq3bDcNVIJ88mmRpMvjF4VdwI0YZt-qQHKlHxr0gQ2_XuRDXNK-HTicDT35Hcx84riahUNEWPDs-OXGVp0mmIdD3J4J1vhLq4hzke94Mc7xr6PP7rxsWsA8m6pxHvr8kxcwSspHspbewP1aFaNxuieDqolx4vJ54_jqQr3YLoq-DHYBNiZCtqBDcMUUwv09S29Et4unb6j540KI6evSZN9r_Jcm4WYWXtDUtAX1Cl18YdhciDgHXOgt0Mh-4CgGzS7RgRvnV04OKlA5h0Gx8uZSYuCZHfRASYPiR1GQyhKkkNUcHvk2_INuesYx56Ad6dsdyXgD5nBQ7b78A8w84i2mGoIGTYWIBO97esWZU8o78FUxqtWfsIpECS4mSJkQSt4LsluIw1OK7Ic6Z9D4mKm0Q8RecIOeSkDHRTBV0FhdJv6RRDKexA-1WjLSFJlO36gTANYUgwzKzA13yPPJZ2zOVmzcgP2jDTVF0tEFiBWa6L0VZvkR1co0y7PdrAn5N3A3XmzgSL_DGHYtUrEeZ0uKdtFARzvGdFOFQeGKUBjN_FUAzVKt21CxCnCOVAaKJZhZ4WdeeVWlDYjHbcXhqY8WK1mwLzGeuCloksmR5zOhcD3USM5EQIpAzvnr0NYeT_Zy2SsQ2N7Pt2Nql359OlKclA3l2wR8Uln6o4mq7JFjLHK2mBSI5Iywki_UjlxXjKGITmWq4VuTJGp1creM48vlE9hY2JiVXq7MX425E65s2ZbgFtcyL4DLweSHD9BMdrGQsMOL-SnmTgJy1Zq5v1f1tmeh3fjalcefpaIn-oUvBscqBc31L-XZbkWVzeRlre2vZutdWWS9hb6uVxg8Eb1xHUNqkzYOxgMhj1Rlgl4Vn902BNoEOYwnUpX9QWJIwe_-w-4e5TxuN39RDt4WAj7N6VKL850VcFCvluC1cPoUt7tVQWqt_Zv5pgnveAWxrzx8R4aF1eIFlUlXnP4kPfEUxrAXM0cxbBhLAcYSyImoIznIJc2T5ckyHw-z6LOKMSYLqVZUCjxEta9CSUQtdxghlMVdZdQtwCC_notoAtiFoh9C8hIHUHCAWlbHB32j447ILOPVLqX1a6RyqvkLUUXq9yuek3wuokuX8Ak-0qvlPguBzqBUbSKMFUSuV2E3N0Yd4fjwQHQlrxMaDEaQ0UpAfds0sPqvFTaML4o7u2JUwntXVh3K_MbauEIkJ1QPASi4GRPXNFGXi7OEOASjkg267CqfihLzN2VzDIsnUvIhr4uktcJt3HUoa1HHw_9sdXAr2JLyXTJT-4Eq8Ndg6IfZc7JMQ5-DW9kkZv3lQvbonyDN_W5xKSyLljjVXwPl7Bfl_aGxpM0zcFGpryNhSfWv71_K56NOob36MOLb4WDXWOMF3QZ7QQHxcMhB7uqrIJT6H3G4TnuzWxtwBtNn2JrKrpbKVJmDJ6p7q72JTDjAlMLedkGPLTf6VQuaeO_4JR8SbShbzgJ06NPtsn1FzbS0BjvyBxU1EkHqTpUsw8muuGzazAxtYXNWzPbhKHUH-8M8iyGKjeAYBp2szMubqSMfqYb0WgXNMQDDEC5rpu4AG9kKtXus52ckDTZ7KJmXJABn1ZxyBFk9l0x5-Gjjw2-lanZNUCYRhjQ8JxcSwYHmYG4wNeCc3JVhAHsEWXBcp7ZpoYi2BF6aOFkk7Ft8CUKjZtEfuY1bli0yLiU7MckZb068rGHj57Rfisw7Eprz-OEUh5hJUNlYBPty5yLnmFBwBgHnOyCEDUXXlHCQWKi4YG43FSKSs6odnYeMw3bZS9Ow96fL8lfcEqhnatoitQKoEdHCIUi1fwTK7MOOZFonUBwUtoE3BTr2kCfKBmxUumSDB8NaKXutqU_Odu6vvbLfL2tDCJ_-93Zm5PTDmXvWfEDi2L_B7U6fC5CUr1KnG4d_AyGTZUqoaIhVFPPcpU2GSxKwyJ4vldAS3WFW_e0Bjgrx_O-lMJrLvJxOhKgLL5IW0aUZjV2y5oz1eTDNil_z7cyLsjmqgVvf7WAnEI1aj6PdbjkUSsO9H0NTThHRRq0MfEZYu0MTaqqo4Ds6Z6oPxCauxL1M0rIU3Epp2C9dgj6Q7ECwvhUl2HLihKi7WpBSZCJjCuk_tkmbqM0ymndN3cwnJOtw-1xQRoVSzTAIOcLkg8ISs5BNFIhUgCFX28IfrCZTblG3F_LahC5vAtUj565fytQ7UrfJ7Guiur5AmQyfA4WiV1uIOkbwMBMxYy_zApNZdIuxoScOuoXLdNDGwuWcEK1gSINt-HWqVhVz5pS8W0NZO235WeB14Wg0_5qdoFw-9v5haOjc5I9nKwh89gM5h74O5S7DwweiMJdA4PfP71js91ilD4N9o3eaYUTt7pahuNIMG_Ruypn_eeHUgKP5IIuPrIQqgRD9yB0MjQFh9kA8svqePQxxDc4vbRr-PCmxb7jUbh4ZogySZq2G7kYeltRAWtEeU1orbKNvWnvVxKrCiwrHj8Koaji_BYdMeGDbuTJmqJUE6ii2wA1JEmhqYfhZM_qHwaW0c6sPoR6VNlLdQoZh5ZXdHqsd2nVrE5vvsLFHA8RYM7pSBwZIQtm70XAAGdII1_KjC46cDDaU-gH4mBXCv07NymODzcuIJzR0Cal-iuz5cIU9824xCoeYytCnczE6yIcEiYmTE9_xe7spheQenS84qIe5bk6kc5DbqXIY5V-jOsyNVMdJ2xHj55i__-d1GjnynWKee6zXHZU9LZpyqsC2d6SlVzHTZBctg5M0NyHzLoreNuEs1tthMy4mKtaykroeey133TbKpa_j-kWmGniPK8O2Cx-iw0gRZPhvDhUQie7Rch1qZRcopitW2J3KXTPqB-IvJ1rcWhKltqEqiubhvP9TpV1u9yzxZrCsd3-dl8vlsx6KqMvqKQvHHegqgExx-TXYdMm1HEZJscaMLeCfwcj1UB3rynropJVCsJWyqCH647of_To-fO3QsmuJHqaTMMPlSD6T2_gC8-SUwzZUc2oEX-iuMknf-6Jk9pTUZQXp9VSp_45mgB5whBeeV9HonRalJpOrFINFMgW2YvvnFLmVlOB0_RdT7yevBILZ4Ei4I464bqU8SDUdg0PDvtPnybiMhE_qeJG4R18kDpsDJ1ATp3rMr2TNz1xDkRxdRSln6a59EvS2o-K9oUNWj2xtlAgd-Lv_P8LzAsuWMzmGrP_D5pMKqYpETKiv4tarSTuOvQwOZ9M35yzfOOOSdiz-Af-zsCuLP4yeZF8T79MVFVNeSGXQk2qNmE_pcOva6XEZEa_1KIUaNjzibhaG4DFa99UTp1pQgspu6lEjEEb5ywpUgxhAsidgkVspeKH4-PjeJpgkspMFVrGH7FoLCd9O8kK3Q8JstYPwkyMXCpdANwyT-BpF9aH-IEaTcT7RHwPKKwxVlx-5_R8riosn82g3tXOWK6omoKMamPgzHvizVJbqseqq-UtqdEZRu4I1jo5w6QGPQMZn5wQniavE3EFqCybWsh7ChXSkzHINAU1rDh8o0xGuV4BA3FVqrSpOkf8vG4VQ8YCSH6nLMENMvHWr8E5crtYh0IwLoMcPuvzEZgvwGb45F__-S-e-fpH:1tokOd:__fF1rTAom0YjtfyXYwmXSL5rZnC3rq9zMjMhmONLFM','2025-03-16 14:34:23.182494');
INSERT INTO "django_session" VALUES ('re058hoebsk6mzb1cusf79nfso5rv2z1','.eJxVjMEOwiAQRP-FsyEsFAGP3v0GsrCLrRqalPZk_Hdp0oPOaTJvZt4i4raOcWu8xInERVhx-s0S5ifXHdAD632Wea7rMiW5V-RBm7zNxK_r0f07GLGNfa0DWNLaWxWITWEH4HDIYM6MtngKRikokLqDLusxkwqKqQyucy0-X8cQN0I:1twvdZ:Ezmg9PJTcr78y8hi4gMSSb1FTK4sBQwpZ5HJJZpHR-o','2025-04-08 04:11:37.527062');
INSERT INTO "django_session" VALUES ('adze8fgk3z42mf224zs2ffsgryeroxn7','.eJxVjMEOwiAQRP-FsyEsFAGP3v0GsrCLrRqalPZk_Hdp0oPOaTJvZt4i4raOcWu8xInERVhx-s0S5ifXHdAD632Wea7rMiW5V-RBm7zNxK_r0f07GLGNfa0DWNLaWxWITWEH4HDIYM6MtngKRikokLqDLusxkwqKqQyucy0-X8cQN0I:1twvny:a-UWW83ZvL3e3tm70pkS6fz705B8nZ8bqfl4WemF54w','2025-04-08 04:22:22.024132');
INSERT INTO "django_session" VALUES ('fvr1yg43ci91rqmnarp295mfutl8a0mg','.eJxVjMsOwiAQRf-FtSEtAwO4dO83kGGGStXQpI-V8d-1SRe6veec-1KJtrWmbSlzGkWdlVWn3y0TP0rbgdyp3SbNU1vnMetd0Qdd9HWS8rwc7t9BpaV-6wAGo7HowIL4QcD3oY_IEKlD6NAgZ0KOnYRYAESiuJ4HYOszgfPq_QGqaTb1:1tyJ1e:dbnaX77lI1R7GXDzs_A2uD1ACG9fSc5D7Mp0u6m3qq0','2025-04-11 23:22:10.614342');
INSERT INTO "django_session" VALUES ('rj7aanxymy6alscb6hebcr0tl3lhs6wo','.eJxVjMsOwiAQRf-FtSGU14BL934DYRiQqoGktCvjv2uTLnR7zzn3xULc1hq2kZcwEzszzU6_G8b0yG0HdI_t1nnqbV1m5LvCDzr4tVN-Xg7376DGUb-11RktFu9EUbnYSaABUAZQSqGjFtJ4wuTBligpJ3LOQgEFzk2QsDj2_gDeRDfF:1u1DDQ:WJ6sgNW08TYuMXjChGix5GXh1dDcu9jVqXIeeYbDc0k','2025-04-19 23:46:20.893363');
INSERT INTO "material_exam" VALUES (1,'test','sdasdfa','2025-02-17 16:33:26.892997',NULL);
INSERT INTO "material_exam" VALUES (2,'1','123','2025-02-18 13:32:54.806420',NULL);
INSERT INTO "material_exam_questions" VALUES (1,1,1);
INSERT INTO "material_exam_questions" VALUES (2,1,2);
INSERT INTO "material_exam_questions" VALUES (3,1,3);
INSERT INTO "material_exam_questions" VALUES (4,2,2);
INSERT INTO "material_exam_questions" VALUES (5,2,3);
INSERT INTO "material_examtemplate" VALUES (1,'institution_logos/icons-5030998_640.png','uai1','ing sistemas','oge','tito puente',2022,'final','escrito','notas 1','tpicos 1','2025-03-15 17:06:42.381973',5);
INSERT INTO "material_examtemplate" VALUES (2,'institution_logos/fondo_4.jpg','dfgasdfgad','adfb','adb','aeffbaedb',1977,'parcial','oral','baqeqbtqwwtbwt','etbqetbrwb','2025-03-15 22:31:24.942960',5);
INSERT INTO "material_examtemplate" VALUES (5,'institution_logos/logo_UAI.png','Universidad Abierta Interamericana','Maestría en Tecnología Educativa','Simuladores y videojuegos','Mg. Gabriela Friedman',2025,'final','escrito','Guarda al pomo','* Cómo se juega al Doom
* Candy Crush o Tetris: debate','2025-03-15 23:04:25.690170',5);
INSERT INTO "material_examtemplate" VALUES (7,'institution_logos/logo_UAI_zQUcn9K.png','dpofmq','g543','34g0j34g0','nm4o5',888,'final','oral','4un42ngo2','24g24j24j24j','2025-03-16 16:46:07.514787',5);
INSERT INTO "material_examtemplate" VALUES (8,'institution_logos/logo_UAI_OCHeCim.png','uai','ing sis','prog 2','menendez',2025,'final','escrito','fgasrgasdg','fgqerg','2025-03-20 22:31:54.799444',5);
INSERT INTO "material_material" VALUES (1,'materials/Clase_2_-_contexto.pptx','2025-02-12 21:00:59.399156','tete',NULL);
INSERT INTO "material_material" VALUES (2,'materials/Clase_2_-_contexto_iQ7RkzI.pptx','2025-02-13 02:04:35.332938','t4',NULL);
INSERT INTO "material_material" VALUES (3,'materials/Clase_2_-_contexto.pdf','2025-02-13 02:07:42.376670','8n8',NULL);
INSERT INTO "material_material" VALUES (4,'materials/Clase_2_-_contexto_fB9tMjI.pdf','2025-02-13 17:47:27.907390','4t',NULL);
INSERT INTO "material_material" VALUES (5,'materials/Clase_2_-_contexto_5VUTSWQ.pdf','2025-02-13 22:11:55.504908','4t33t',NULL);
INSERT INTO "material_material" VALUES (6,'materials/Clase_2_-_contexto.pdf','2025-02-13 22:13:04.956544','fgndfn',NULL);
INSERT INTO "material_material" VALUES (7,'materials/Clase_2_-_contexto.pptx','2025-02-14 01:51:13.732833','1',NULL);
INSERT INTO "material_material" VALUES (8,'materials/Clase_3_-_Politica_de_negocios.pptx','2025-02-14 02:24:10.309178','1',NULL);
INSERT INTO "material_material" VALUES (9,'materials/Clase_2_-_contexto_73rIzeP.pptx','2025-02-14 04:13:43.582850','1',NULL);
INSERT INTO "material_material" VALUES (10,'materials/Clase_2_-_contexto_lyhWWDY.pptx','2025-02-14 04:40:45.796474','1',NULL);
INSERT INTO "material_material" VALUES (11,'materials/Clase_2_-_contexto_XRiDIpz.pdf','2025-02-14 04:40:51.801476','1',NULL);
INSERT INTO "material_material" VALUES (12,'materials/Clase_2_-_contexto_fQQ5vL0.pptx','2025-02-14 04:50:24.643012','1',NULL);
INSERT INTO "material_material" VALUES (13,'materials/Clase_4_-_Actividad_en_clase.pptx','2025-02-14 12:38:08.759937','1',NULL);
INSERT INTO "material_material" VALUES (14,'materials/Clase_4_-_Actividad_en_clase_ytSO0QZ.pptx','2025-02-14 13:35:38.734817','1',NULL);
INSERT INTO "material_material" VALUES (15,'materials/mariachi.png','2025-02-14 15:09:52.796638','foto',NULL);
INSERT INTO "material_material" VALUES (22,'materials/OGE-_aspectos_éticos_y_legales.pdf','2025-02-14 22:10:34.166528','eqdqe',3);
INSERT INTO "material_material" VALUES (23,'materials/OGE-_aspectos_éticos_y_legales_PuMM72I.pdf','2025-02-14 22:18:43.779456','sfg',3);
INSERT INTO "material_material" VALUES (25,'','2025-02-15 23:37:52.571059','Material por Defecto',4);
INSERT INTO "material_material" VALUES (27,'materials/Clase_6_-_Estructura_6RojG18.pptx','2025-02-17 15:16:38.304285','frg454eg',4);
INSERT INTO "material_material" VALUES (28,'materials/1º_parcial__2024_OGE_-_Tema_1.docx','2025-02-18 23:18:46.385862','parcial1',4);
INSERT INTO "material_material" VALUES (29,'materials/1º_parcial__2024_OGE_-_Tema_1.pdf','2025-02-18 23:22:11.026265','p1',4);
INSERT INTO "material_material" VALUES (30,'materials/CONSTRUCCION_ciudadania1.pdf','2025-02-20 15:50:36.235481','ciud',4);
INSERT INTO "material_material" VALUES (31,'materials/Grosso_-_Claves_para_el_desarrollo_de_la_empresa-75-102.pdf','2025-02-20 15:56:54.663054','cap estrategia',4);
INSERT INTO "material_material" VALUES (36,'materials/Stephen_P._Robbins__Timothy_A._Judge_-_Comportamiento_organizacional_recurso_e_qh0Vpwz.pdf','2025-03-02 14:21:42.759246','1',5);
INSERT INTO "material_material" VALUES (38,'materials/template_examen.doc','2025-03-17 01:54:40.230173','template',5);
INSERT INTO "material_profile" VALUES (1,'user',3);
INSERT INTO "material_profile" VALUES (2,'admin',4);
INSERT INTO "material_profile" VALUES (4,'admin',5);
INSERT INTO "material_question" VALUES (1,'Tendencias de cambio estructural ("marco global")','Se refiere a fenómenos internacionales que afectan el desarrollo de los negocios.
Factores clave:
Globalización económica y cultural.
Desarrollo tecnológico e industrias emergentes.
Cambios demográficos y sociales.
Regulaciones medioambientales a escala global.
Determina las condiciones futuras del mercado y guía la estrategia a largo plazo.','contexto','ambitos',44,25,'2',1,3);
INSERT INTO "material_question" VALUES (2,'que gusto tiene la sal?','salado','salitud','salita',78886,25,'19816918',1,4);
INSERT INTO "material_question" VALUES (3,'azucar','dulce','celia','cruz',98779,25,'79',1,5);
INSERT INTO "material_question" VALUES (4,X'50726567756e74613a20504b030414000600080000002100c39604c3995155030000c3be100000140000007070742f70726573656e746174696f6e2e786d6cc3acc297c3916ec39b2014c286c3af27c3ad1d2cc39f4ec2a903c2b6c2b11335c2a9c3926dc299267552c395760f406dc2925ac385c38602c392c2b5c29dc3b6c3ae3b10c29cc290504dc29576c29bc2ab60c3bec383c38fc3a17338c286c3b3c28bc3a7c296474f4cc2aa4674c2b318c29dc28dc3a3c28875c295c2a8c29b6e3dc28b7fc39e2d47651c294dc2bbc29a72c391c2b159c3bcc382547c31c3bfc3b8c3a1c2bcc29fc3b6c29229c39669c2aa61680436c29dc29ac39259c3bcc2a0753f4d12553dc2b0c296c2aa33c391c2b30ec2b4c295c2902dc395c3b028c397492dc3a92fc2b06f79c282c38763c292c2b4c2b4c3a962375ec2be67c2bc58c2adc29ac28a7d11c395c2a6c285c3a9c2b726c29271c29bc2877a687a35c2b8c3b5c3af71c3b35771c298c292c2a24fc3ac7673c2afc2985ec28a4e2bc2a013c38f61c399c28ac3973fc2a8c3924c7ec2afc2afc2943ec3aac289c29a7a1663c2941559c299c2920cc398c389c2a9c3a90105c385c389c3bc3c796b78273453c3bfc3aac39bc29bc3a0c39cc2b9c2bc3506c29c0fc39bc39b6472c3a265c281c38dc3b84379c3a2c389c3a9c2b1c29cc2a2c38cc293c2b350c3b6c38d6d72c28732c3b66412c38ac2a92717c2814cc386c29e5cc286c2a3c3bdc38c27c3a168c3a4c3931f073ac3b6c39dc2917d3dc287c3a3c3bdc39c51002ec38507c3be2139c3a22f0ec285c3a8c2884f16c285c3ac48c3aec3ab213cc3a2c2a3476fc3902bc2a8c3a2c2b1c3bc56c382c2b2c39b5ce281a4c2b2c2b1c3a14f21c2b2c382c2b1c39cc2b2c2bbc2bac39bc2b2c2b0c2b0c2bac39fc2afc2b2c2b2c2b15cc2b2c2b145e3808dc2b2c383c382c2b0c2b1c2b8c2b0c2b157c2a8c382c2aac2b1c2b0c2a8c2b0c2a8c389c2b020c2bcc2b8c2b1c2b0c2b0c382c2b0c2b1c2a67e21c2a8c2b1c2b27ec2a6c2b1c39bc2b17ee281b820c2a6c2b17ec2b0c388c2bac2bac2b1c2a3c2a3','Respuesta generada por IA','Tema generado por IA','Subtema generado por IA',1,27,NULL,1,3);
INSERT INTO "material_question" VALUES (5,'Respuesta: [Respuesta generada por IA]','Respuesta generada por IA','Tema generado por IA','Subtema generado por IA',1,27,NULL,1,4);
INSERT INTO "material_question" VALUES (6,X'50726567756e74613a20504b030414000600080000002100c299557e05c3b9000000c3a10200000b0008025f72656c732f2e72656c7320c2a2040228c2a000020000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000003d28e2978f295c72','Respuesta generada por IA','Tema generado por IA','Subtema generado por IA',1,28,NULL,1,5);
INSERT INTO "material_question" VALUES (7,'For purposes of classification, \(()\) consists of a list of all occurrences of \(','Respuesta generada por IA','Tema generado por IA','Subtema generado por IA',1,28,NULL,1,3);
INSERT INTO "material_question" VALUES (8,'\) within \({([x,x)]\)). Therefore each occurrence corresponds to all occurrences of \({([x,x])]\), but not \({([x,x])]\).','Respuesta generada por IA','Tema generado por IA','Subtema generado por IA',1,28,NULL,1,4);
INSERT INTO "material_question" VALUES (9,'For simplicity reasons, \(()\) consists of the \(`x\) element list. Thus \(()\) has three properties, which make \(()\) the','Respuesta generada por IA','Tema generado por IA','Subtema generado por IA',1,28,NULL,1,5);
INSERT INTO "material_question" VALUES (10,'Respuesta: [Respuesta generada por IA]','Respuesta generada por IA','Tema generado por IA','Subtema generado por IA',1,28,NULL,1,3);
INSERT INTO "material_question" VALUES (11,'Pregunta: %PDF-1.7','Respuesta generada por IA','Tema generado por IA','Subtema generado por IA',1,29,NULL,1,4);
INSERT INTO "material_question" VALUES (12,'%µµµµ','Respuesta generada por IA','Tema generado por IA','Subtema generado por IA',1,29,NULL,1,5);
INSERT INTO "material_question" VALUES (13,'1 0 obj','Respuesta generada por IA','Tema generado por IA','Subtema generado por IA',1,29,NULL,1,3);
INSERT INTO "material_question" VALUES (14,'<</Type/Catalog/Pages 2 0 R/Lang(en) /StructTreeRoot 25 0 R/MarkInfo<</Marked true>>/Metadata 267 0 R/ViewerPreferences 268 0 R>>','Respuesta generada por IA','Tema generado por IA','Subtema generado por IA',1,29,NULL,1,4);
INSERT INTO "material_question" VALUES (15,'endobj','Respuesta generada por IA','Tema generado por IA','Subtema generado por IA',1,29,NULL,1,5);
INSERT INTO "material_question" VALUES (16,'2 0 obj','Respuesta generada por IA','Tema generado por IA','Subtema generado por IA',1,29,NULL,1,3);
INSERT INTO "material_question" VALUES (17,'<</Type/Pages/Count 1/Kids[ 3 0 R] >>','Respuesta generada por IA','Tema generado por IA','Subtema generado por IA',1,29,NULL,1,4);
INSERT INTO "material_question" VALUES (18,'endobj','Respuesta generada por IA','Tema generado por IA','Subtema generado por IA',1,29,NULL,1,5);
INSERT INTO "material_question" VALUES (19,'3 0 obj','Respuesta generada por IA','Tema generado por IA','Subtema generado por IA',1,29,NULL,1,3);
INSERT INTO "material_question" VALUES (20,'<</Type/Page/Parent 2 0 R/Resources<</Font<</F1 5 0 R/F2 9 0 R/F3 12 0 R/F4 17 0 R/F5 19 0 R>>/ExtGState<</GS7 7 0 R/GS8 8 0 R>>/XObject<</Image11 11 0 R>>/ProcSet[/PDF/Text/Image/View] 11 0 R/Procedure<</Procedure>/(?5 + (3 | 9 )))/(?2 + (25 | 24)))/(?0.7 + (4 | 2))))/Dict 5 6 R/Proc[L]/<Words,Dictionary,Number>,/<Words.Elements,Numbers> 5 6 R/ProcR[L]/<Words,Dictionary.Elements,Numbers> 5 6.','Respuesta generada por IA','Tema generado por IA','Subtema generado por IA',1,29,NULL,1,4);
INSERT INTO "material_question" VALUES (21,'Respuesta: [Respuesta generada por IA]','Respuesta generada por IA','Tema generado por IA','Subtema generado por IA',1,29,NULL,1,5);
INSERT INTO "material_question" VALUES (22,'Pregunta: %PDF-1.7','Respuesta generada por IA','Tema generado por IA','Subtema generado por IA',1,29,NULL,1,3);
INSERT INTO "material_question" VALUES (23,'%µµµµ','Respuesta generada por IA','Tema generado por IA','Subtema generado por IA',1,29,NULL,1,4);
INSERT INTO "material_question" VALUES (24,'1 0 obj','Respuesta generada por IA','Tema generado por IA','Subtema generado por IA',1,29,NULL,1,5);
INSERT INTO "material_question" VALUES (25,'<</Type/Catalog/Pages 2 0 R/Lang(en) /StructTreeRoot 25 0 R/MarkInfo<</Marked true>>/Metadata 267 0 R/ViewerPreferences 268 0 R>>','Respuesta generada por IA','Tema generado por IA','Subtema generado por IA',1,29,NULL,1,3);
INSERT INTO "material_question" VALUES (26,'endobj','Respuesta generada por IA','Tema generado por IA','Subtema generado por IA',1,29,NULL,1,4);
INSERT INTO "material_question" VALUES (27,'2 0 obj','Respuesta generada por IA','Tema generado por IA','Subtema generado por IA',1,29,NULL,1,5);
INSERT INTO "material_question" VALUES (28,'<</Type/Pages/Count 1/Kids[ 3 0 R] >>','Respuesta generada por IA','Tema generado por IA','Subtema generado por IA',1,29,NULL,1,3);
INSERT INTO "material_question" VALUES (29,'endobj','Respuesta generada por IA','Tema generado por IA','Subtema generado por IA',1,29,NULL,1,4);
INSERT INTO "material_question" VALUES (30,'3 0 obj','Respuesta generada por IA','Tema generado por IA','Subtema generado por IA',1,29,NULL,1,5);
INSERT INTO "material_question" VALUES (31,'<</Type/Page/Parent 2 0 R/Resources<</Font<</F1 5 0 R/F2 9 0 R/F3 12 0 R/F4 17 0 R/F5 19 0 R>>/ExtGState<</GS7 7 0 R/GS8 8 0 R>>/XObject<</Image11 11 0 R>>/ProcSet[/PDF/Text/Image/Font8 11R/Folder1/Folder2/Group1/Group3/Group4/Group5/Group6]>','Respuesta generada por IA','Tema generado por IA','Subtema generado por IA',1,29,NULL,1,3);
INSERT INTO "material_question" VALUES (32,'endobj','Respuesta generada por IA','Tema generado por IA','Subtema generado por IA',1,29,NULL,1,4);
INSERT INTO "material_question" VALUES (33,'endobj','Respuesta generada por IA','Tema generado por IA','Subtema generado por IA',1,29,NULL,1,5);
INSERT INTO "material_question" VALUES (34,'0/S1_2 <</Font>> <</Font> <Page>%><Type>HTML</Type> %> 0 </Page> <Page>%><Type> PDF</Type> %> 0 </Page> <Page>%><Type> PDF</Type> %> 1 </Page>','Respuesta generada por IA','Tema generado por IA','Subtema generado por IA',1,29,NULL,1,3);
INSERT INTO "material_question" VALUES (35,'Respuesta: [Respuesta generada por IA]','Respuesta generada por IA','Tema generado por IA','Subtema generado por IA',1,29,NULL,1,4);
INSERT INTO "material_question" VALUES (36,X'50726567756e74613a20504b030414000600080000002100c299557e05c3b9000000c3a10200000b0008025f72656c732f2e72656c7320c2a2040228c2a000020000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000003d285b3f5d3d28293f3d28282e2a293f2e283f3a29283f3a29285b3f5d29285b3f5d29283f2929293f3a28283f28285b3f5d3d28293f28285b3f5d3d28293f28283f28285b3f5d3d283f28285b3f5d3d283f28285b3f5d3d285b3f28285b3f5d3d283f28285b3f5d3d285b213f28285b3f5d3d285b3f28283f28285b2a3f28285b3f28285b5b3f5d3d285b283f2928285b2a3f28285b5b7e28285b2a7e2828','Respuesta generada por IA','Tema generado por IA','Subtema generado por IA',1,28,NULL,1,5);
INSERT INTO "material_question" VALUES (37,'Respuesta: [Respuesta generada por IA]','Respuesta generada por IA','Tema generado por IA','Subtema generado por IA',1,28,NULL,1,3);
INSERT INTO "material_question" VALUES (38,'y estructura? Estructura organizacional Debe reflejar: Responsables de las tareas. Responsables de los resultados. Debe reflejar: Flexible: puede ser modificada con cierta facilidad. Simple: economa de recursos. Simple: economa de recursos.','Respuesta generada por IA','Tema generado por IA','Subtema generado por IA',1,27,NULL,1,4);
INSERT INTO "material_question" VALUES (39,'el griego: strategos, vo- cablo conel que se designaba al general del antiguo ejercito helénico cuya función era disponer los planes de batallas y conducir las maniobras del ejercito en el terreno del combate.','Respuesta generada por IA','Tema generado por IA','Subtema generado por IA',1,31,NULL,1,5);
INSERT INTO "material_question" VALUES (40,'Pregunta 1: La palabra “estrategia” proviene del griego: strategos, vo- cablo conel que se designaba al general del antiguo ejercito helénico cuya función era disponer los planes de batallas y conducir las maniobras del ejercito en el terreno del combate.','Respuesta generada por IA','Tema generado por IA','Subtema generado por IA',1,31,NULL,1,3);
INSERT INTO "material_question" VALUES (41,'Pregunta 20: encontraramos en la esencia misma de la moderna administración de los negocios.','Respuesta generada por IA','Tema generado por IA','Subtema generado por IA',1,31,NULL,1,4);
INSERT INTO "material_question" VALUES (42,'Pregunta 7: del griego: strategos, vo- cablo conel que se designaba al general del antiguo ejercito helénico cuya función era disponer los planes de batallas y conducir las maniobras del ejercito en el terreno del combate.','Respuesta generada por IA','Tema generado por IA','Subtema generado por IA',1,31,NULL,1,5);
INSERT INTO "material_subjects" VALUES (1,'name','Inicial');
CREATE INDEX IF NOT EXISTS "auth_group_permissions_group_id_b120cbf9" ON "auth_group_permissions" (
	"group_id"
);
CREATE UNIQUE INDEX IF NOT EXISTS "auth_group_permissions_group_id_permission_id_0cd325b0_uniq" ON "auth_group_permissions" (
	"group_id",
	"permission_id"
);
CREATE INDEX IF NOT EXISTS "auth_group_permissions_permission_id_84c5c92e" ON "auth_group_permissions" (
	"permission_id"
);
CREATE INDEX IF NOT EXISTS "auth_permission_content_type_id_2f476e4b" ON "auth_permission" (
	"content_type_id"
);
CREATE UNIQUE INDEX IF NOT EXISTS "auth_permission_content_type_id_codename_01ab375a_uniq" ON "auth_permission" (
	"content_type_id",
	"codename"
);
CREATE INDEX IF NOT EXISTS "auth_user_groups_group_id_97559544" ON "auth_user_groups" (
	"group_id"
);
CREATE INDEX IF NOT EXISTS "auth_user_groups_user_id_6a12ed8b" ON "auth_user_groups" (
	"user_id"
);
CREATE UNIQUE INDEX IF NOT EXISTS "auth_user_groups_user_id_group_id_94350c0c_uniq" ON "auth_user_groups" (
	"user_id",
	"group_id"
);
CREATE INDEX IF NOT EXISTS "auth_user_user_permissions_permission_id_1fbb5f2c" ON "auth_user_user_permissions" (
	"permission_id"
);
CREATE INDEX IF NOT EXISTS "auth_user_user_permissions_user_id_a95ead1b" ON "auth_user_user_permissions" (
	"user_id"
);
CREATE UNIQUE INDEX IF NOT EXISTS "auth_user_user_permissions_user_id_permission_id_14a6b632_uniq" ON "auth_user_user_permissions" (
	"user_id",
	"permission_id"
);
CREATE INDEX IF NOT EXISTS "django_admin_log_content_type_id_c4bce8eb" ON "django_admin_log" (
	"content_type_id"
);
CREATE INDEX IF NOT EXISTS "django_admin_log_user_id_c564eba6" ON "django_admin_log" (
	"user_id"
);
CREATE UNIQUE INDEX IF NOT EXISTS "django_content_type_app_label_model_76bd3d3b_uniq" ON "django_content_type" (
	"app_label",
	"model"
);
CREATE INDEX IF NOT EXISTS "django_session_expire_date_a5c62663" ON "django_session" (
	"expire_date"
);
CREATE INDEX IF NOT EXISTS "material_exam_created_by_id_70c44f2a" ON "material_exam" (
	"created_by_id"
);
CREATE INDEX IF NOT EXISTS "material_exam_questions_exam_id_7fe9d1b3" ON "material_exam_questions" (
	"exam_id"
);
CREATE UNIQUE INDEX IF NOT EXISTS "material_exam_questions_exam_id_question_id_e54e40b5_uniq" ON "material_exam_questions" (
	"exam_id",
	"question_id"
);
CREATE INDEX IF NOT EXISTS "material_exam_questions_question_id_46c3d35b" ON "material_exam_questions" (
	"question_id"
);
CREATE INDEX IF NOT EXISTS "material_examtemplate_created_by_id_1c62d7cd" ON "material_examtemplate" (
	"created_by_id"
);
CREATE INDEX IF NOT EXISTS "material_material_uploaded_by_id_9f6a6102" ON "material_material" (
	"uploaded_by_id"
);
CREATE INDEX IF NOT EXISTS "material_question_material_id" ON "material_question" (
	"material_id"
);
CREATE INDEX IF NOT EXISTS "material_question_subject_id" ON "material_question" (
	"subject_id"
);
CREATE INDEX IF NOT EXISTS "material_question_user_id" ON "material_question" (
	"user_id"
);
COMMIT;
