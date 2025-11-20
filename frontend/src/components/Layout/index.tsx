import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  LayoutDashboard,
  Heart,
  Users,
  Calendar,
  Settings,
  Menu,
  X,
  Sparkles,
  CircleUser
} from "lucide-react";
import cn from "classnames"
import styles from "./index.module.scss";

const navigation = [
  { name: "Dashboard", href: "/", icon: LayoutDashboard },
  { name: "Health", href: "/health", icon: Heart },
  { name: "Receivables", href: "/receivables", icon: Users },
  { name: "Payments", href: "/payments", icon: Calendar },
  { name: "Settings", href: "/settings", icon: Settings },
];

export default function Layout({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <div className={styles.root}>
      <aside className={styles.sidebar}>
        <div className={styles.sidebarInner}>
          <Link to="/" className={styles.brandLink} title="FinFlow">
            <Sparkles />
          </Link>
          {/* <Link to="/login" className={styles.brandLink} title="auth">
            <CircleUser />
          </Link> */}
          <nav className={styles.nav} aria-label="Primary">
            {navigation.map((item) => {
              const isActive = location.pathname === item.href;
              const Icon = item.icon;
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={cn(styles.navItem, isActive && styles.navItemActive)}
                  title={item.name}
                >
                  <Icon />
                  <div className={styles.tooltip}>{item.name}</div>
                </Link>
              );
            })}
          </nav>
        </div>
      </aside>

      {/* Mobile menu */}
      <div className={styles.mobileHeader}>
        <div className={styles.mobileBar}>
          <div className={styles.mobileInner}>
            <button
              type="button"
              className={styles.btn}
              onClick={() => setMobileMenuOpen(true)}
              aria-label="Open menu"
            >
              <Menu />
            </button>

            <div className={styles.brandRow}>
              <div className={styles.brandSmall}>
                <Sparkles className="h-4 w-4 text-primary-foreground" />
              </div>
              <span className={styles.appName}>FinFlow</span>
            </div>

            <div style={{ width: 40 }} />
          </div>
        </div>

        {mobileMenuOpen && (
          <div>
            <div className={styles.mobilePanelOverlay} onClick={() => setMobileMenuOpen(false)} />
            <div className={styles.mobilePanel} role="dialog" aria-modal="true">
              <div className={styles.menuCloseRow}>
                <div className={styles.brandRow}>
                  <div className={styles.brandSmall}>
                    <Sparkles className="h-5 w-5 text-primary-foreground" />
                  </div>
                  <span className={styles.appName}>FinFlow</span>
                </div>
                <button
                  onClick={() => setMobileMenuOpen(false)}
                  aria-label="Close menu"
                  className={styles.btn}
                >
                  <X />
                </button>
              </div>

              <nav className={styles.mobileNav}>
                <ul className={styles.navList}>
                  {navigation.map((item) => {
                    const isActive = location.pathname === item.href;
                    const Icon = item.icon;
                    return (
                      <li className={styles.navListItem} key={item.name}>
                        <Link
                          to={item.href}
                          onClick={() => setMobileMenuOpen(false)}
                          className={cn(styles.navListItemLink, isActive && styles.navItemActive)}
                        >
                          <Icon />
                          <span className={styles.navItemText}>{item.name}</span>
                        </Link>
                      </li>
                    );
                  })}
                </ul>
              </nav>
            </div>
          </div>
        )}
      </div>

      {/* Main content */}
      <main className={styles.main}>
        <div className={styles.contentWrap}>{children}</div>
      </main>
    </div>
  );
}
