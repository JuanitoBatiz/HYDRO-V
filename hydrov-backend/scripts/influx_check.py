import asyncio, os, sys
sys.path.insert(0, '')

async def check():
    from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync
    url    = os.getenv('INFLUX_URL',   'http://influxdb:8086')
    token  = os.getenv('INFLUX_TOKEN', '')
    org    = os.getenv('INFLUX_ORG',   'hydrov')
    bucket = os.getenv('INFLUX_BUCKET_TELEMETRY', 'sensor_telemetry')
    print(f"Bucket: {bucket} | URL: {url}")

    async with InfluxDBClientAsync(url=url, token=token, org=org) as client:
        q = client.query_api()

        r2 = await q.query(f'from(bucket:"{bucket}") |> range(start:-31d) |> keep(columns:["device_code"]) |> distinct(column:"device_code")')
        print("DEVICE CODES en InfluxDB:")
        for t in r2:
            for rec in t.records:
                print(f"  '{rec.get_value()}'")

        r3 = await q.query(f'from(bucket:"{bucket}") |> range(start:-2h) |> count() |> sum()')
        print("Puntos en las ultimas 2h:")
        for t in r3:
            for rec in t.records:
                print(f"  {rec.get_measurement()} {rec.get_field()} = {rec.get_value()}")

        r4 = await q.query(f'from(bucket:"{bucket}") |> range(start:-31d) |> last()')
        print("Ultimo punto (cualquier device):")
        shown = 0
        for t in r4:
            for rec in t.records:
                if shown < 3:
                    print(f"  t={rec.get_time()} dev={rec.values.get('device_code')} field={rec.get_field()} val={rec.get_value()}")
                    shown += 1

asyncio.run(check())
