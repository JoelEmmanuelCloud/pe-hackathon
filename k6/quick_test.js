import http from "k6/http";
import { check, sleep } from "k6";

const BASE_URL = __ENV.BASE_URL || "http://167.172.165.216";

export const options = {
  stages: [
    { duration: "15s", target: 50 },
    { duration: "30s", target: 50 },
    { duration: "15s", target: 0 },
  ],
  thresholds: {
    http_req_failed: ["rate<0.05"],
  },
};

export default function () {
  const h = http.get(`${BASE_URL}/health`);
  check(h, { "health 200": (r) => r.status === 200 });

  const l = http.get(`${BASE_URL}/urls`);
  check(l, { "urls 200": (r) => r.status === 200 });

  const s = http.post(`${BASE_URL}/shorten`,
    JSON.stringify({ original_url: `https://example.com/${Math.random()}` }),
    { headers: { "Content-Type": "application/json" } }
  );
  check(s, { "shorten 201": (r) => r.status === 201 });

  sleep(1);
}
