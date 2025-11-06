import { Card, CardContent, CardHeader, CardTitle } from "../../ui/card";
import { Badge } from "../../ui/badge";
import { Building2 } from "lucide-react";
import styles from "./index.module.scss";

const accounts = [
  {
    bank: "Tinkoff",
    balance: 285000,
    currency: "₽",
    lastSync: "2 мин назад",
    status: "active",
  },
  {
    bank: "Sberbank",
    balance: 142000,
    currency: "₽",
    lastSync: "5 мин назад",
    status: "active",
  },
  {
    bank: "Alfa-Bank",
    balance: 53000,
    currency: "₽",
    lastSync: "1 час назад",
    status: "active",
  },
];

export default function BankAccountsList() {
  return (
    <Card className={styles.bankCard}>
      <CardHeader className={styles.bankCardHeader}>
        <div className={styles.headerGroup}>
          <div className={styles.headerIconBg}>
            <Building2 className={styles.headerIcon} />
          </div>
          <div>
            <CardTitle className={styles.bankCardTitle}>Банковские счета</CardTitle>
            <p className={styles.bankCardSubtitle}>
              Все подключенные счета в одном месте
            </p>
          </div>
        </div>
      </CardHeader>
      <CardContent className={styles.bankCardContent}>
        <div className={styles.accountList}>
          {accounts.map((account) => (
            <div
              key={account.bank}
              className={styles.accountItem}
            >
              <div className={styles.itemDetails}>
                <div className={styles.itemIconBg}>
                  <Building2 className={styles.itemIcon} />
                </div>
                <div>
                  <p className={styles.itemBank}>{account.bank}</p>
                  <p className={styles.itemSync}>
                    актуален: {account.lastSync}
                  </p>
                </div>
              </div>
              <div className={styles.itemBalance}>
                <p className={styles.balanceAmount}>
                  {account.currency}
                  {account.balance.toLocaleString()}
                </p>
                <Badge className={styles.statusBadge}>активен</Badge>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}