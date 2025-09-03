CREATE VIEW block_summary AS
SELECT b.block_id,
       b.start_time,
       b.end_time,
       SUM(bt.layover_minutes) AS total_layovers,
       SUM(bb.break_duration)  AS total_breaks
FROM blocks b
LEFT JOIN block_trips bt ON b.block_id = bt.block_id
LEFT JOIN block_breaks bb ON b.block_id = bb.block_id
GROUP BY b.block_id, b.start_time, b.end_time;
