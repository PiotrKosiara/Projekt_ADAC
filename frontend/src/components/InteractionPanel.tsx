import { useMemo, useState } from "react";

type Product = {
  id: string;
  title: string;
  category: string;
  price: string;
  rating: number;
};

const products: Product[] = [
  { id: "product-1", title: "Kamera IP Sentinel", category: "Monitoring", price: "899 PLN", rating: 4.7 },
  { id: "product-2", title: "Klucz FIDO2 Titan", category: "Identity", price: "289 PLN", rating: 4.9 },
  { id: "product-3", title: "Router SecureMesh", category: "Network", price: "649 PLN", rating: 4.4 },
  { id: "product-4", title: "Vault Password Suite", category: "Software", price: "79 PLN/mies", rating: 4.6 },
];

export function InteractionPanel() {
  const [selectedCategory, setSelectedCategory] = useState<string>("Wszystkie");
  const [search, setSearch] = useState("");
  const [newsletter, setNewsletter] = useState(false);
  const [agreed, setAgreed] = useState(false);

  const filteredProducts = useMemo(() => {
    return products.filter((product) => {
      const byCategory = selectedCategory === "Wszystkie" || product.category === selectedCategory;
      const bySearch = product.title.toLowerCase().includes(search.toLowerCase());
      return byCategory && bySearch;
    });
  }, [selectedCategory, search]);

  return (
    <section className="panel surface">
      <header className="panel-header">
        <h2>Interaktywny Testbed Ruchu</h2>
        <p>Eksploruj elementy jak w e-commerce, aby wygenerować naturalną trajektorię kursora.</p>
      </header>

      <nav className="menu-row" aria-label="Główne menu">
        <button id="menu-home" className="menu-btn">Start</button>
        <button id="menu-products" className="menu-btn">Produkty</button>
        <button id="menu-about" className="menu-btn">O projekcie</button>
        <button id="menu-contact" className="menu-btn">Kontakt</button>
      </nav>

      <div className="control-grid">
        <div className="control-card">
          <label htmlFor="search-input">Wyszukiwarka produktów</label>
          <input
            id="search-input"
            type="text"
            value={search}
            placeholder="np. router"
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>

        <div className="control-card">
          <span>Filtr kategorii</span>
          <div className="chip-row">
            {["Wszystkie", "Monitoring", "Identity", "Network", "Software"].map((option) => (
              <button
                key={option}
                id={`filter-${option.toLowerCase()}`}
                className={selectedCategory === option ? "chip chip-active" : "chip"}
                onClick={() => setSelectedCategory(option)}
              >
                {option}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="product-grid">
        {filteredProducts.map((product) => (
          <article key={product.id} id={product.id} className="product-card">
            <h3>{product.title}</h3>
            <p className="muted">{product.category}</p>
            <p className="price">{product.price}</p>
            <p className="rating">Ocena: {product.rating}</p>
            <div className="product-actions">
              <button id={`${product.id}-details`} className="secondary-btn">
                Szczegóły
              </button>
              <button id={`${product.id}-cart`} className="primary-btn">
                Dodaj do koszyka
              </button>
            </div>
          </article>
        ))}
      </div>

      <form className="form-grid" onSubmit={(event) => event.preventDefault()}>
        <label htmlFor="email-input">Newsletter bezpieczeństwa</label>
        <input id="email-input" type="email" placeholder="email@domena.pl" />

        <div className="toggle-row">
          <label className="toggle-item" htmlFor="newsletter-toggle">
            <input
              id="newsletter-toggle"
              type="checkbox"
              checked={newsletter}
              onChange={(event) => setNewsletter(event.target.checked)}
            />
            Otrzymuj alerty o podatnościach
          </label>

          <label className="toggle-item" htmlFor="agree-toggle">
            <input
              id="agree-toggle"
              type="checkbox"
              checked={agreed}
              onChange={(event) => setAgreed(event.target.checked)}
            />
            Akceptuję regulamin testbedu
          </label>
        </div>

        <button id="cta-buy" className="cta-btn" disabled={!agreed}>
          Finalizuj próbny zakup
        </button>
      </form>
    </section>
  );
}
