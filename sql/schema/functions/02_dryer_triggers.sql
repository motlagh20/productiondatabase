CREATE FUNCTION app.mark_loading_unloaded() RETURNS trigger AS $$
BEGIN
  UPDATE app.dryer_loading
  SET is_unloaded = TRUE
  WHERE load_id = NEW.load_id;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_unloading_sets_loading_unloaded
AFTER INSERT ON app.dryer_unloading
FOR EACH ROW
EXECUTE FUNCTION app.mark_loading_unloaded();

