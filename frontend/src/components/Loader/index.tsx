import css from "./index.module.scss";

export const Loader = () => (
  <div className={css.loader}>
    <span className={css.bar}></span>
    <span className={css.bar}></span>
    <span className={css.bar}></span>
  </div>
);
