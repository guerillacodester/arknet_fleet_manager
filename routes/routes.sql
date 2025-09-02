/*
 Navicat Premium Dump SQL

 Source Server         : arknettransit
 Source Server Type    : PostgreSQL
 Source Server Version : 160009 (160009)
 Source Host           : 127.0.0.1:5432
 Source Catalog        : arknettransit
 Source Schema         : public

 Target Server Type    : PostgreSQL
 Target Server Version : 160009 (160009)
 File Encoding         : 65001

 Date: 02/09/2025 21:22:09
*/


-- ----------------------------
-- Table structure for routes
-- ----------------------------
DROP TABLE IF EXISTS "public"."routes";
CREATE TABLE "public"."routes" (
  "id" int4 NOT NULL DEFAULT nextval('routes_id_seq'::regclass),
  "route" text COLLATE "pg_catalog"."default" NOT NULL,
  "route_path" text COLLATE "pg_catalog"."default"
)
;

-- ----------------------------
-- Primary Key structure for table routes`x
-- ----------------------------
ALTER TABLE "public"."routes" ADD CONSTRAINT "routes_pkey" PRIMARY KEY ("id");
