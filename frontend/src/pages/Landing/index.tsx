import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { AuthModal } from "../Auth";
import { Button } from "../../ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../../ui/card";
import {
  TrendingUp,
  Shield,
  Zap,
  BarChart3,
  ArrowRight,
  CheckCircle,
  Sparkles,
} from "lucide-react";
import styles from "./index.module.scss";

export default function Landing() {
  const [isAuthOpen, setIsAuthOpen] = useState(false);
  const navigate = useNavigate();

  const features = [
    {
      icon: BarChart3,
      title: "Финансовая аналитика",
      description: "Получайте детальную аналитику по всем вашим счетам в одном месте",
    },
    {
      icon: TrendingUp,
      title: "Прогноз денежных потоков",
      description: "ML-прогнозы помогают предсказать кассовые разрывы заранее",
    },
    {
      icon: Shield,
      title: "Безопасность",
      description: "Ваши данные защищены современными стандартами безопасности",
    },
    {
      icon: Zap,
      title: "Мультибанкинг",
      description: "Подключите счета из разных банков и управляйте ими централизованно",
    },
  ];

  const benefits = [
    "Автоматическая синхронизация с банками",
    "Управление дебиторской задолженностью",
    "Прогнозирование денежных потоков",
    "Детальная финансовая аналитика",
    "Отслеживание всех транзакций",
  ];

  return (
    <div className={styles.landing}>
      <AuthModal isOpen={isAuthOpen} onClose={() => setIsAuthOpen(false)} />

      {/* Hero Section */}
      <section className={styles.hero}>
        <div className={styles.heroContent}>
          <div className={styles.brand}>
            <Sparkles className={styles.brandIcon} />
            <span className={styles.brandName}>FinFlow</span>
          </div>
          <h1 className={styles.heroTitle}>
            Управление финансами для предпринимателей
          </h1>
          <p className={styles.heroDescription}>
            Объедините все ваши банковские счета, получите детальную аналитику и прогнозы денежных потоков в одном приложении
          </p>
          <div className={styles.heroActions}>
            <Button
              size="lg"
              onClick={() => setIsAuthOpen(true)}
              className={styles.ctaButton}
            >
              Начать бесплатно
              <ArrowRight size={20} />
            </Button>
            <Button
              size="lg"
              variant="outline"
              onClick={() => {
                setIsAuthOpen(true);
                setTimeout(() => {
                  const loginTab = document.querySelector('[data-view="login"]');
                  if (loginTab) (loginTab as HTMLElement).click();
                }, 100);
              }}
            >
              Войти
            </Button>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className={styles.features}>
        <div className={styles.sectionContent}>
          <h2 className={styles.sectionTitle}>Возможности</h2>
          <div className={styles.featuresGrid}>
            {features.map((feature, index) => {
              const Icon = feature.icon;
              return (
                <Card key={index} className={styles.featureCard}>
                  <CardHeader>
                    <div className={styles.featureIcon}>
                      <Icon />
                    </div>
                    <CardTitle>{feature.title}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p>{feature.description}</p>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </div>
      </section>

      {/* Benefits Section */}
      <section className={styles.benefits}>
        <div className={styles.sectionContent}>
          <div className={styles.benefitsGrid}>
            <div className={styles.benefitsText}>
              <h2 className={styles.sectionTitle}>Почему FinFlow?</h2>
              <p className={styles.benefitsDescription}>
                Мы помогаем предпринимателям эффективно управлять финансами, предсказывать проблемы и принимать обоснованные решения
              </p>
              <ul className={styles.benefitsList}>
                {benefits.map((benefit, index) => (
                  <li key={index} className={styles.benefitItem}>
                    <CheckCircle className={styles.checkIcon} />
                    <span>{benefit}</span>
                  </li>
                ))}
              </ul>
              <Button
                size="lg"
                onClick={() => setIsAuthOpen(true)}
                className={styles.ctaButton}
              >
                Попробовать бесплатно
                <ArrowRight size={20} />
              </Button>
            </div>
            <div className={styles.benefitsVisual}>
              <Card className={styles.visualCard}>
                <CardContent className={styles.visualContent}>
                  <div className={styles.chartPlaceholder}>
                    <BarChart3 size={64} />
                    <p>Интерактивные графики и аналитика</p>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className={styles.cta}>
        <div className={styles.sectionContent}>
          <Card className={styles.ctaCard}>
            <CardContent className={styles.ctaContent}>
              <h2 className={styles.ctaTitle}>Готовы начать?</h2>
              <p className={styles.ctaDescription}>
                Присоединяйтесь к предпринимателям, которые уже используют FinFlow для управления финансами
              </p>
              <Button
                size="lg"
                onClick={() => setIsAuthOpen(true)}
                className={styles.ctaButtonLarge}
              >
                Создать аккаунт
                <ArrowRight size={20} />
              </Button>
            </CardContent>
          </Card>
        </div>
      </section>
    </div>
  );
}

