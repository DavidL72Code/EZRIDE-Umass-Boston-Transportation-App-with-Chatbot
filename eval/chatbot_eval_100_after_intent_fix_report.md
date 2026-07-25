# Chatbot Eval Report

- Run: 2026-07-23T20:23:07
- Total: 100
- Passed: 98
- Failed: 2
- Pass rate: 98.0%

## Results

| ID | Type | Status | Checks | Sources | Map focus |
|---|---|---:|---|---:|---:|
| live_shuttle_campus_center_01 | live_shuttle_arrival | PASS | must_include_any=yes, must_not_source_media=yes, must_not_map_focus=yes | 1 | 0 |
| live_shuttle_jfk_02 | live_shuttle_arrival | PASS | must_include_any=yes, must_not_source_media=yes, must_not_map_focus=yes | 1 | 0 |
| live_shuttle_bayside_03 | live_shuttle_arrival | PASS | must_include_any=yes, must_not_source_media=yes, must_not_map_focus=yes | 0 | 0 |
| live_shuttle_library_04 | live_shuttle_arrival | PASS | must_include_any=yes, must_not_source_media=yes, must_not_map_focus=yes | 1 | 0 |
| live_shuttle_mt_vernon_05 | live_shuttle_arrival | PASS | must_include_any=yes, must_not_source_media=yes | 0 | 0 |
| live_shuttle_nearest_06 | live_shuttle_arrival | PASS | must_include_any=yes, must_not_source_media=yes | 1 | 1 |
| live_red_ashmont_07 | live_mbta_arrival | PASS | must_include_any=yes, must_not_source_media=yes | 1 | 0 |
| live_red_jfk_08 | live_mbta_arrival | PASS | must_include_any=yes, must_not_source_media=yes | 1 | 0 |
| live_orange_forest_hills_09 | live_mbta_arrival | PASS | must_include_any=yes, must_not_source_media=yes | 1 | 0 |
| live_green_northeastern_10 | live_mbta_arrival | PASS | must_include_any=yes, must_not_source_media=yes | 1 | 0 |
| live_bus_16_11 | live_mbta_arrival | PASS | must_include_any=yes, must_not_source_media=yes | 1 | 0 |
| live_bus_8_12 | live_mbta_arrival | PASS | must_include_any=yes, must_not_source_media=yes | 1 | 1 |
| live_train_nearest_13 | live_mbta_arrival | PASS | must_include_any=yes, must_not_source_media=yes | 3 | 0 |
| live_bus_nearest_14 | live_mbta_arrival | PASS | must_include_any=yes, must_not_source_media=yes | 3 | 0 |
| live_no_location_15 | live_mbta_arrival | PASS | must_include_any=yes, must_not_source_media=yes | 1 | 0 |
| parking_ambiguous_16 | parking_clarification | PASS | must_include_all=yes, must_not_source_media=yes | 1 | 0 |
| parking_price_17 | parking_rate_specific | PASS | must_include_all=yes, must_not_source_media=yes | 3 | 0 |
| parking_price_18 | parking_rate_specific | PASS | must_include_any=yes, must_not_source_media=yes | 3 | 0 |
| parking_price_19 | parking_rate_specific | PASS | must_include_any=yes, must_not_source_media=yes | 4 | 0 |
| parking_price_20 | parking_rate_specific | PASS | must_include_any=yes, must_not_source_media=yes | 4 | 0 |
| parking_price_21 | parking_rate_specific | PASS | must_include_any=yes, must_not_source_media=yes | 3 | 0 |
| parking_price_22 | parking_rate_specific | PASS | must_include_any=yes, must_not_source_media=yes | 3 | 0 |
| parking_evening_23 | parking_rate_specific | PASS | must_include_any=yes, must_not_source_media=yes | 3 | 0 |
| parking_payment_24 | parking_process | PASS | must_include_any=yes, must_not_source_media=yes | 4 | 0 |
| parking_payment_25 | parking_process | PASS | must_include_any=yes, must_not_source_media=yes | 3 | 0 |
| parking_nearest_26 | parking_near_me | PASS | must_include_any=yes, must_not_source_media=yes | 1 | 0 |
| parking_nearest_27 | parking_near_me | PASS | must_include_any=yes, must_not_source_media=yes | 2 | 0 |
| parking_no_location_28 | parking_near_me_no_location | PASS | must_include_any=yes, must_not_source_media=yes | 1 | 0 |
| parking_locations_29 | parking_info | PASS | must_include_any=yes, must_not_source_media=yes | 3 | 0 |
| parking_garages_30 | parking_info | PASS | must_include_any=yes, must_not_source_media=yes | 2 | 0 |
| parking_reserved_31 | parking_info | PASS | must_include_any=yes, must_not_source_media=yes | 2 | 0 |
| parking_ticket_32 | rag_policy | PASS | must_include_any=yes, must_not_source_media=yes | 2 | 0 |
| parking_ticket_33 | rag_policy | PASS | must_include_any=yes, must_not_source_media=yes | 2 | 0 |
| parking_towed_34 | rag_policy | PASS | must_include_any=yes, must_not_source_media=yes | 3 | 0 |
| parking_permit_35 | rag_policy | PASS | must_include_any=yes, must_not_source_media=yes | 3 | 0 |
| parking_permit_36 | rag_fact | PASS | must_include_any=yes, must_not_source_media=yes | 3 | 0 |
| parking_permit_37 | rag_fact | PASS | must_include_any=yes, must_not_source_media=yes | 3 | 0 |
| parking_permit_38 | rag_fact | PASS | must_include_any=yes, must_not_source_media=yes | 2 | 0 |
| parking_fine_39 | rag_fact | PASS | must_include_any=yes, must_not_source_media=yes | 4 | 0 |
| parking_fine_40 | rag_fact | PASS | must_include_any=yes, must_not_source_media=yes | 3 | 0 |
| media_campus_41 | media_request | PASS | must_include_any=yes, must_source_media=yes, must_source_pdf=yes, must_source_image=yes | 2 | 0 |
| media_subway_42 | media_request | PASS | must_include_any=yes, must_source_media=yes, must_source_pdf=yes | 1 | 0 |
| media_system_43 | media_request | PASS | must_include_any=yes, must_source_media=yes, must_source_pdf=yes | 1 | 0 |
| media_downtown_44 | media_request | PASS | must_include_any=yes, must_source_media=yes, must_source_pdf=yes | 3 | 0 |
| media_bus_45 | media_request | PASS | must_include_any=yes, must_source_media=yes, must_source_pdf=yes | 1 | 0 |
| media_ferry_46 | media_request | PASS | must_include_any=yes, must_source_media=yes, must_source_pdf=yes | 1 | 0 |
| media_commuter_47 | media_request | PASS | must_include_any=yes, must_source_media=yes, must_source_pdf=yes | 1 | 0 |
| media_zones_48 | media_request | PASS | must_include_any=yes, must_source_media=yes, must_source_pdf=yes | 2 | 0 |
| media_bike_49 | media_request | PASS | must_include_any=yes, must_source_media=yes, must_source_pdf=yes | 1 | 0 |
| media_red_map_50 | media_request | PASS | must_include_any=yes, must_source_media=yes, must_source_pdf=yes | 1 | 0 |
| media_orange_map_51 | media_request | PASS | must_include_any=yes, must_source_media=yes, must_source_pdf=yes | 1 | 0 |
| media_green_map_52 | media_request | PASS | must_include_any=yes, must_source_media=yes, must_source_pdf=yes | 1 | 0 |
| media_blue_map_53 | media_request | PASS | must_include_any=yes, must_source_media=yes, must_source_pdf=yes | 1 | 0 |
| media_parking_map_54 | media_request | PASS | must_include_any=yes, must_source_media=yes | 2 | 0 |
| media_no_live_55 | media_request | PASS | must_include_any=yes, must_source_media=yes | 5 | 0 |
| directions_56 | directions_intent | PASS | must_include_any=yes, no_media_unless_explicit=yes | 3 | 0 |
| directions_57 | directions_intent | PASS | must_include_any=yes, no_media_unless_explicit=yes | 3 | 0 |
| directions_58 | directions_intent | PASS | must_include_any=yes, no_media_unless_explicit=yes | 4 | 0 |
| route_59 | route_knowledge | PASS | must_include_any=yes, must_not_source_media=yes | 3 | 0 |
| route_60 | route_knowledge | PASS | must_include_any=yes, must_not_source_media=yes | 4 | 0 |
| route_61 | route_knowledge | PASS | must_include_any=yes, must_not_source_media=yes | 3 | 0 |
| route_62 | route_knowledge | PASS | must_include_any=yes, must_not_source_media=yes | 4 | 0 |
| route_63 | route_knowledge | PASS | must_include_any=yes, must_not_source_media=yes | 4 | 0 |
| route_64 | detour_fallback | PASS | must_include_any=yes, must_not_source_media=yes | 4 | 0 |
| route_65 | detour_fallback | PASS | must_include_any=yes, must_not_source_media=yes | 3 | 0 |
| route_66 | detour_fallback | PASS | must_include_any=yes, must_not_source_media=yes | 3 | 0 |
| route_67 | route_knowledge | PASS | must_include_any=yes, must_not_source_media=yes | 2 | 0 |
| route_68 | route_knowledge | PASS | must_include_any=yes, must_not_source_media=yes | 3 | 0 |
| rag_69 | rag_policy | PASS | must_include_any=yes, must_not_source_media=yes | 2 | 0 |
| rag_70 | rag_policy | PASS | must_include_any=yes, must_not_source_media=yes | 2 | 0 |
| rag_71 | rag_policy | PASS | must_include_any=yes, must_not_source_media=yes | 2 | 0 |
| rag_72 | rag_policy | PASS | must_include_any=yes, must_not_source_media=yes | 2 | 0 |
| rag_73 | rag_policy | FAIL | must_include_any=no, must_not_source_media=yes | 2 | 0 |
| rag_74 | rag_fact | PASS | must_include_any=yes, must_not_source_media=yes | 3 | 0 |
| rag_75 | rag_fact | PASS | must_include_any=yes, must_not_source_media=yes | 2 | 0 |
| rag_76 | rag_fact | PASS | must_include_any=yes, must_not_source_media=yes | 3 | 0 |
| rag_77 | rag_fact | PASS | must_include_any=yes, must_not_source_media=yes | 4 | 0 |
| rag_78 | rag_fact | PASS | must_include_any=yes, must_not_source_media=yes | 3 | 0 |
| rag_79 | rag_fact | PASS | must_include_any=yes, must_not_source_media=yes | 2 | 0 |
| rag_80 | rag_fact | PASS | must_include_any=yes, must_not_source_media=yes | 2 | 0 |
| rag_81 | rag_policy | PASS | must_include_any=yes, must_not_source_media=yes | 3 | 0 |
| rag_82 | rag_policy | PASS | must_include_any=yes, must_not_source_media=yes | 3 | 0 |
| rag_83 | rag_process | PASS | must_include_any=yes, must_not_source_media=yes | 4 | 0 |
| rag_84 | rag_process | PASS | must_include_any=yes, must_not_source_media=yes | 3 | 0 |
| rag_85 | rag_process | PASS | must_include_any=yes, must_not_source_media=yes | 2 | 0 |
| rag_86 | rag_contact | PASS | must_include_any=yes, must_not_source_media=yes | 2 | 0 |
| rag_87 | rag_contact | PASS | must_include_any=yes, must_not_source_media=yes | 3 | 0 |
| rag_88 | rag_contact | PASS | must_include_any=yes, must_not_source_media=yes | 4 | 0 |
| rag_89 | rag_accessibility | PASS | must_include_any=yes, must_not_source_media=yes | 4 | 0 |
| rag_90 | rag_accessibility | PASS | must_include_any=yes, must_not_source_media=yes | 3 | 0 |
| rag_91 | rag_shuttle | PASS | must_include_any=yes, must_not_source_media=yes | 4 | 0 |
| rag_92 | rag_shuttle | PASS | must_include_any=yes, must_not_source_media=yes | 4 | 0 |
| rag_93 | rag_shuttle | PASS | must_include_any=yes, must_not_source_media=yes | 3 | 0 |
| offtopic_94 | off_topic | PASS | must_include_any=yes, must_not_source_media=yes | 1 | 0 |
| offtopic_95 | off_topic | PASS | must_include_any=yes, must_not_source_media=yes | 3 | 0 |
| offtopic_96 | off_topic | PASS | must_include_any=yes, must_not_source_media=yes | 1 | 0 |
| clarify_97 | clarification | PASS | must_include_any=yes, must_not_source_media=yes | 3 | 0 |
| clarify_98 | clarification | FAIL | must_include_any=no, must_not_source_media=yes | 2 | 0 |
| security_99 | security | PASS | must_include_any=yes, must_not_source_media=yes | 2 | 0 |
| security_100 | security | PASS | must_include_any=yes, must_not_source_media=yes | 4 | 0 |

## Failures

### rag_73

Question: what happens if I lose a commuter rail semester pass?

Checks: `{"must_include_any": false, "must_not_source_media": true}`

Observed: `{"source_count": 2, "media_source_count": 0, "pdf_source_count": 0, "image_source_count": 0, "map_focus_count": 0}`

Answer excerpt: Commuter Rail semester passes are non-refundable and non-replaceable if lost or stolen. The university is not liable for lost or damaged passes, even if they are lost during mail transit.

### clarify_98

Question: where is it?

Checks: `{"must_include_any": false, "must_not_source_media": true}`

Observed: `{"source_count": 2, "media_source_count": 0, "pdf_source_count": 0, "image_source_count": 0, "map_focus_count": 0}`

Answer excerpt: Because your question is broad, here is where various UMass Boston transportation facilities are located:

*   **EV Charging:** You can find 23 ChargePoint ports at the West Garage (15 on the first floor), the Campus Center Garage (4 on the lower level), and the Quad Lot (4).
*   **Bike Parking & Charging:** There are over 740 bike parking spaces campus-wide. The West Garage contains a secure shelter with 125 indoor spaces, a maintenance station, and 13 Saris Power Posts (26 ports) for free e-bi

