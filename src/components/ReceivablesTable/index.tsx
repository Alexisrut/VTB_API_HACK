import { Card, CardContent, CardHeader, CardTitle } from "../../ui/card";
import { Badge } from "../../ui/badge";
import { Button } from "../../ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../../ui/table";
import styles from "./index.module.scss";
import { Phone } from "lucide-react";

const receivables = [
  {
    id: 1,
    counterparty: 'LLC "Client 1"',
    amount: 50000,
    dueDate: "10.10",
    status: "pending",
  },
  {
    id: 2,
    counterparty: 'LLC "Client 2"',
    amount: 35000,
    dueDate: "05.10",
    status: "overdue",
  },
  {
    id: 3,
    counterparty: "IP Petrov",
    amount: 20000,
    dueDate: "12.10",
    status: "pending",
  },
  {
    id: 4,
    counterparty: 'LLC "Customer"',
    amount: 15000,
    dueDate: "01.10",
    status: "overdue",
  },
];

export default function ReceivablesTable() {
  const getStatusBadge = (status: string) => {
    if (status === "overdue") {
      return (
        <Badge className={styles.badgeOverdue}>
          Overdue
        </Badge>
      );
    }
    return (
      <Badge className={styles.badgePending}>
        Pending
      </Badge>
    );
  };

  return (
    <Card className={styles.cardRoot}>
      <CardHeader className={styles.header}>
        <div className={styles.iconBox} aria-hidden>
          <svg className="h-5 w-5 text-success" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <div className={styles.headerText}>
          <CardTitle className={styles.title}>Выплаты</CardTitle>
          <p className={styles.subtitle}>Отслеживайте входящик платежи и управляйте ими</p>
        </div>
      </CardHeader>
      <CardContent className={styles.content}>
        <div className={styles.tableWrap}>
          <Table>
            <TableHeader>
              <TableRow className={styles.tableRow}>
                <TableHead className={styles.counterparty}>Имя</TableHead>
                <TableHead className={styles.amount}>Сумма</TableHead>
                <TableHead className={styles.dueDate}>Дата</TableHead>
                <TableHead>Статус</TableHead>
                {/* <TableHead>Actions</TableHead> */}
              </TableRow>
            </TableHeader>
            <TableBody>
              {receivables.map((item) => (
                <TableRow key={item.id} className={`${styles.tableRow} ${styles.tableRowHover}`}>
                  <TableCell className={styles.counterparty}>{item.counterparty}</TableCell>
                  <TableCell className={styles.amount}>₽{item.amount.toLocaleString()}</TableCell>
                  <TableCell className={styles.dueDate}>{item.dueDate}</TableCell>
                  <TableCell>{getStatusBadge(item.status)}</TableCell>
                  {/* <TableCell>
                    <div className={styles.actions}>
                      <Button variant="outline" size="sm" className={styles.btnOutlineHover}>
                        {item.status === "overdue" ? (
                          <>
                            <Phone className="h-4 w-4 mr-2" />Call
                          </>
                        ) : (
                          "Remind"
                        )}
                      </Button>
                    </div>
                  </TableCell> */}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}
