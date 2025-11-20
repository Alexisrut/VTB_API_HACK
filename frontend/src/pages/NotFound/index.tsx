import css from "./index.module.scss"

export default function NotFound () {
    return (
        <div className={css.pageContainer}>
            <p>Такой страницы не существует</p>
            <img src="/kitty.webp"></img>
        </div>
    )
}