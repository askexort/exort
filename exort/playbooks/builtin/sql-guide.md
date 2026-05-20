# SQL Reference Guide

## Basic Queries
```sql
SELECT column1, column2 FROM table WHERE condition ORDER BY column LIMIT 10;
```

## Joins
```sql
-- INNER JOIN (matching rows only)
SELECT * FROM orders JOIN customers ON orders.customer_id = customers.id;

-- LEFT JOIN (all left + matching right)
SELECT * FROM orders LEFT JOIN customers ON orders.customer_id = customers.id;
```

## Aggregation
```sql
SELECT category, COUNT(*), AVG(price), MAX(price)
FROM products
GROUP BY category
HAVING COUNT(*) > 5;
```

## Window Functions
```sql
SELECT name, salary,
  RANK() OVER (ORDER BY salary DESC) as rank,
  salary - LAG(salary) OVER (ORDER BY salary) as diff
FROM employees;
```

## Common Table Expressions
```sql
WITH active_users AS (
  SELECT user_id FROM orders WHERE date > '2024-01-01'
)
SELECT * FROM users WHERE id IN (SELECT user_id FROM active_users);
```
