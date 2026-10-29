#!/usr/bin/env bash
B=${BASE:-http://localhost}
pass=0; fail=0
check() {
  if [ "$2" = "$3" ]; then echo "PASS  $1  (got $2)"; pass=$((pass+1)); else echo "FAIL  $1  (expected $3, got $2)"; fail=$((fail+1)); fi
}
code() { curl -s -o /dev/null -w '%{http_code}' "$@"; }
J='Content-Type: application/json'
S=$(date +%s)

check "GET /health" "$(code $B/health)" 200
check "health body" "$(curl -s $B/health)" '{"cache":"ok","db":"ok","status":"ok"}'

U=$(curl -s -X POST $B/users -H "$J" -d "{\"username\":\"tester$S\",\"email\":\"t$S@example.com\"}")
UID_=$(echo "$U" | sed -n 's/.*"id": *\([0-9]*\).*/\1/p')
check "POST /users creates user" "$([ -n "$UID_" ] && echo yes)" yes
check "POST /users duplicate -> 409" "$(code -X POST $B/users -H "$J" -d "{\"username\":\"tester$S\",\"email\":\"t$S@example.com\"}")" 409
check "GET /users/<id>" "$(code $B/users/$UID_)" 200

R=$(curl -s -w '\n%{http_code}' -X POST $B/shorten -H "$J" -d "{\"original_url\":\"https://example.com/a\",\"title\":\"Guide\",\"user_id\":$UID_}")
check "POST /shorten -> 201" "$(echo "$R" | tail -1)" 201
C=$(echo "$R" | head -1 | sed -n 's/.*"short_code": *"\([^"]*\)".*/\1/p')
ID=$(echo "$R" | head -1 | sed -n 's/.*"id": *\([0-9]*\).*/\1/p')
check "POST /shorten no original_url -> 400" "$(code -X POST $B/shorten -H "$J" -d '{"title":"x"}')" 400
check "POST /shorten ftp:// -> 400" "$(code -X POST $B/shorten -H "$J" -d '{"original_url":"ftp://x"}')" 400
check "POST /shorten unknown user -> 404" "$(code -X POST $B/shorten -H "$J" -d '{"original_url":"https://x.com","user_id":999999}')" 404
check "POST /shorten not JSON -> 400" "$(code -X POST $B/shorten -d 'hello')" 400

check "GET /<code> miss -> 302" "$(code $B/$C)" 302
check "redirect target" "$(curl -s -o /dev/null -w '%{redirect_url}' $B/$C)" https://example.com/a
check "GET /<code> hit -> 302" "$(code $B/$C)" 302
check "click_count after 3 visits" "$(curl -s $B/stats/$C | sed -n 's/.*"click_count": *\([0-9]*\).*/\1/p')" 3
check "GET /zzzzzz unknown -> 404" "$(code $B/zzzzzz$S)" 404
check "GET /stats unknown -> 404" "$(code $B/stats/zzzzzz)" 404

check "GET /urls -> 200" "$(code $B/urls)" 200
check "GET /urls?page=0 -> 400" "$(code "$B/urls?page=0")" 400
check "GET /urls?user_id filter" "$(curl -s "$B/urls?user_id=$UID_" | sed -n 's/.*"total": *\([0-9]*\).*/\1/p')" 1
check "GET /urls/<id> -> 200" "$(code $B/urls/$ID)" 200
check "GET /urls/999999 -> 404" "$(code $B/urls/999999)" 404

check "PUT /urls/<id> -> 200" "$(code -X PUT $B/urls/$ID -H "$J" -d '{"original_url":"https://example.com/b"}')" 200
check "update clears cache" "$(curl -s -o /dev/null -w '%{redirect_url}' $B/$C)" https://example.com/b

check "GET /events?url_id -> 200" "$(code "$B/events?url_id=$ID")" 200
check "POST /events -> 201" "$(code -X POST $B/events -H "$J" -d "{\"url_id\":$ID,\"event_type\":\"shared\"}")" 201

check "DELETE /urls/<id> -> 200" "$(code -X DELETE $B/urls/$ID)" 200
check "deactivated link -> 410" "$(code $B/$C)" 410
check "DELETE /urls/999999 -> 404" "$(code -X DELETE $B/urls/999999)" 404

M=$(curl -s $B/metrics)
for m in http_requests_total http_request_duration_seconds_count cache_lookups_total url_redirects_total active_urls_total process_cpu_percent; do
  check "metric $m" "$(echo "$M" | grep -q "^$m" && echo present)" present
done

echo; echo "$pass passed, $fail failed"
