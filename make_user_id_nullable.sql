-- Script to modify pod_schedules table to make user_id nullable
-- Run this in the Supabase SQL Editor

-- First, drop the foreign key constraint if it exists
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'pod_schedules_user_id_fkey' 
        AND table_name = 'pod_schedules'
    ) THEN
        ALTER TABLE pod_schedules DROP CONSTRAINT pod_schedules_user_id_fkey;
    END IF;
END $$;

-- Then modify the column to allow NULL values
ALTER TABLE pod_schedules ALTER COLUMN user_id DROP NOT NULL;

-- Verify the changes
SELECT 
    column_name, 
    data_type, 
    is_nullable 
FROM 
    information_schema.columns 
WHERE 
    table_name = 'pod_schedules' 
    AND column_name = 'user_id'; 