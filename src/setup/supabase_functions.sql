-- Create function to execute arbitrary SQL (WARNING: This is potentially dangerous!)
-- This should be used only for setup and development purposes
CREATE OR REPLACE FUNCTION exec_sql(query text)
RETURNS JSON
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  EXECUTE query;
  RETURN json_build_object('success', true);
EXCEPTION WHEN others THEN
  RETURN json_build_object('success', false, 'error', SQLERRM);
END;
$$;