# Chatbot Eval Report

- Run: 2026-07-23T19:51:45
- Total: 25
- Passed: 25
- Failed: 0
- Pass rate: 100.0%

## Results

| ID | Type | Status | Checks | Sources | Map focus |
|---|---|---:|---|---:|---:|
| live_shuttle_campus_center | live_shuttle_arrival | PASS | must_include_any=yes, must_not_source_media=yes, must_not_map_focus=yes | 1 | 0 |
| live_shuttle_jfk | live_shuttle_arrival | PASS | must_include_any=yes, must_not_source_media=yes, must_not_map_focus=yes | 1 | 0 |
| live_red_line_ashmont | live_mbta_arrival | PASS | must_include_any=yes, must_not_source_media=yes | 1 | 0 |
| live_route_16_forest_hills | live_mbta_arrival | PASS | must_include_any=yes, must_not_source_media=yes | 1 | 0 |
| ambiguous_parking_cost | parking_clarification | PASS | must_include_all=yes, must_not_source_media=yes | 1 | 0 |
| west_garage_cost | parking_rate_specific | PASS | must_include_all=yes, must_not_source_media=yes | 3 | 0 |
| quad_lot_cost | parking_rate_specific | PASS | must_include_any=yes, must_not_source_media=yes | 4 | 0 |
| nearest_parking_with_location | parking_near_me | PASS | must_include_any=yes, must_not_source_media=yes | 1 | 0 |
| nearest_parking_without_location | parking_near_me_no_location | PASS | must_include_any=yes, must_not_source_media=yes | 1 | 0 |
| campus_map_media | media_request | PASS | must_include_any=yes, must_source_media=yes, must_source_pdf=yes, must_source_image=yes | 2 | 0 |
| mbta_subway_map_media | media_request | PASS | must_include_any=yes, must_source_media=yes, must_source_pdf=yes | 1 | 0 |
| commuter_rail_map_media | media_request | PASS | must_include_any=yes, must_source_media=yes, must_source_pdf=yes | 1 | 0 |
| ferry_map_media | media_request | PASS | must_include_any=yes, must_source_media=yes, must_source_pdf=yes | 1 | 0 |
| bike_map_media | media_request | PASS | must_include_any=yes, must_source_media=yes, must_source_pdf=yes | 1 | 0 |
| campus_center_directions | directions_intent | PASS | must_include_any=yes, no_media_unless_explicit=yes | 3 | 0 |
| ashmont_to_campus_route | route_knowledge | PASS | must_include_any=yes, must_not_source_media=yes | 3 | 0 |
| forest_hills_to_campus_route | route_knowledge | PASS | must_include_any=yes, must_not_source_media=yes | 4 | 0 |
| red_line_outage_fallback | detour_fallback | PASS | must_include_any=yes, must_not_source_media=yes | 4 | 0 |
| semester_pass | rag_policy | PASS | must_include_any=yes, must_not_source_media=yes | 2 | 0 |
| parking_ticket_21_days | rag_policy | PASS | must_include_any=yes, must_not_source_media=yes | 2 | 0 |
| ev_charging_ports | rag_fact | PASS | must_include_any=yes, must_not_source_media=yes | 3 | 0 |
| bluebikes_price | rag_fact | PASS | must_include_any=yes, must_not_source_media=yes | 3 | 0 |
| bike_locker | rag_fact | PASS | must_include_any=yes, must_not_source_media=yes | 2 | 0 |
| shuttle_ads | rag_process | PASS | must_include_any=yes, must_not_source_media=yes | 4 | 0 |
| off_topic | off_topic | PASS | must_include_any=yes, must_not_source_media=yes | 1 | 0 |
