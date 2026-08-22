import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-landing',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="min-h-screen bg-gray-50">
      <!-- Navigation -->
      <nav class="bg-white shadow-sm fixed w-full top-0 z-50">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div class="flex justify-between items-center h-16">
            <div class="flex items-center">
              <h1 class="text-2xl font-bold gradient-text">AUSTIAL</h1>
              <span class="ml-3 text-sm text-gray-500">Powered by GIFT City IFSC</span>
            </div>
            <div class="hidden md:flex space-x-8">
              <a href="#problem" class="text-gray-700 hover:text-blue-600">Problem</a>
              <a href="#solution" class="text-gray-700 hover:text-blue-600">Solution</a>
              <a href="#demo" class="text-gray-700 hover:text-blue-600">Demo</a>
              <a href="#pitch" class="text-gray-700 hover:text-blue-600">Pitch Deck</a>
            </div>
            <a routerLink="/login" class="gradient-bg text-white px-6 py-2 rounded-lg hover:opacity-90 transition">
              Launch App
            </a>
          </div>
        </div>
      </nav>

      <!-- Hero Section -->
      <section class="gradient-bg pt-32 pb-20 px-4">
        <div class="max-w-7xl mx-auto">
          <div class="text-center text-white mb-12">
            <h1 class="text-5xl md:text-7xl font-bold mb-6">
              Fractional RWA Tokenization<br/>
              <span class="text-yellow-300">for GIFT City</span>
            </h1>
            <p class="text-xl md:text-2xl mb-8 text-blue-100 max-w-4xl mx-auto">
              IFSCA-compliant platform enabling NRI/foreign investors to access fractional Indian real estate,
              commodities, and infrastructure via registered-form tokens
            </p>
            <div class="flex flex-col sm:flex-row gap-4 justify-center">
              <a href="#demo" class="bg-white text-blue-900 px-8 py-4 rounded-lg font-semibold hover:bg-blue-50 transition text-lg">
                Watch Demo Video
              </a>
              <a routerLink="/register" class="border-2 border-white text-white px-8 py-4 rounded-lg font-semibold hover:bg-white hover:text-blue-900 transition text-lg">
                Start Free Trial
              </a>
            </div>
          </div>

          <!-- Key Stats -->
          <div class="grid grid-cols-2 md:grid-cols-4 gap-6 mt-16">
            <div class="bg-white bg-opacity-10 backdrop-blur-lg rounded-xl p-6 text-center">
              <div class="text-5xl font-bold text-yellow-300">$10-50B</div>
              <div class="text-blue-100 mt-2">Tokenizable Assets<br/>by 2030</div>
            </div>
            <div class="bg-white bg-opacity-10 backdrop-blur-lg rounded-xl p-6 text-center">
              <div class="text-5xl font-bold text-yellow-300">5-6 sec</div>
              <div class="text-blue-100 mt-2">FCSS Settlement<br/>vs. 3-5 days SWIFT</div>
            </div>
            <div class="bg-white bg-opacity-10 backdrop-blur-lg rounded-xl p-6 text-center">
              <div class="text-5xl font-bold text-yellow-300">&lt;1%</div>
              <div class="text-blue-100 mt-2">Issuance Fees<br/>vs. 3-4% traditional</div>
            </div>
            <div class="bg-white bg-opacity-10 backdrop-blur-lg rounded-xl p-6 text-center">
              <div class="text-5xl font-bold text-yellow-300">24</div>
              <div class="text-blue-100 mt-2">Entities Built<br/>MVP Complete</div>
            </div>
          </div>
        </div>
      </section>

      <!-- Video Demo Section -->
      <section id="demo" class="py-20 bg-white">
        <div class="max-w-6xl mx-auto px-4">
          <div class="text-center mb-12">
            <h2 class="text-4xl font-bold text-gray-900 mb-4">See Austial in Action</h2>
            <p class="text-xl text-gray-600">Full end-to-end investor flywheel: Funding → KYC → Subscribe → Hold → Redeem</p>
          </div>

          <!-- Video Embed -->
          <div class="relative pb-[56.25%] h-0 overflow-hidden rounded-2xl shadow-2xl mb-8">
            <iframe
              class="absolute top-0 left-0 w-full h-full"
              src="https://www.youtube.com/embed/dQw4w9WgXcQ"
              title="Austial Platform Demo"
              frameborder="0"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowfullscreen>
            </iframe>
          </div>

          <div class="text-center">
            <p class="text-gray-600 mb-4">Or try the live interactive app:</p>
            <a routerLink="/login" class="gradient-bg text-white px-8 py-3 rounded-lg inline-block hover:opacity-90 transition">
              Launch App →
            </a>
          </div>
        </div>
      </section>

      <!-- Problem Section -->
      <section id="problem" class="py-20 bg-gray-50">
        <div class="max-w-7xl mx-auto px-4">
          <div class="text-center mb-16">
            <h2 class="text-4xl font-bold text-gray-900 mb-4">The Problem</h2>
            <p class="text-xl text-gray-600 max-w-3xl mx-auto">
              High-value assets remain inaccessible to 99% of investors due to illiquidity, high minimums, and slow cross-border settlement
            </p>
          </div>

          <div class="grid md:grid-cols-2 gap-8">
            <div class="bg-white rounded-2xl p-8 shadow-lg hover:shadow-2xl transition">
              <div class="text-red-600 text-3xl mb-4">🚫</div>
              <h3 class="text-2xl font-bold mb-4">For Investors</h3>
              <ul class="space-y-3 text-gray-700">
                <li class="flex items-start">
                  <span class="text-red-500 mr-2">✗</span>
                  <span><strong>₹1Cr+ minimums</strong> for traditional AIFs (vs. ₹10L fractional)</span>
                </li>
                <li class="flex items-start">
                  <span class="text-red-500 mr-2">✗</span>
                  <span><strong>5-10 day</strong> cross-border settlement via SWIFT</span>
                </li>
                <li class="flex items-start">
                  <span class="text-red-500 mr-2">✗</span>
                  <span><strong>No secondary liquidity</strong> — capital locked for years</span>
                </li>
                <li class="flex items-start">
                  <span class="text-red-500 mr-2">✗</span>
                  <span><strong>Opaque ownership records</strong> in spreadsheets</span>
                </li>
              </ul>
            </div>

            <div class="bg-white rounded-2xl p-8 shadow-lg hover:shadow-2xl transition">
              <div class="text-red-600 text-3xl mb-4">💸</div>
              <h3 class="text-2xl font-bold mb-4">For Issuers</h3>
              <ul class="space-y-3 text-gray-700">
                <li class="flex items-start">
                  <span class="text-red-500 mr-2">✗</span>
                  <span><strong>3-4% placement fees</strong> for traditional capital raise</span>
                </li>
                <li class="flex items-start">
                  <span class="text-red-500 mr-2">✗</span>
                  <span><strong>Narrow investor reach</strong> without expensive agents</span>
                </li>
                <li class="flex items-start">
                  <span class="text-red-500 mr-2">✗</span>
                  <span><strong>Manual cap table management</strong> — reconciliation risk</span>
                </li>
                <li class="flex items-start">
                  <span class="text-red-500 mr-2">✗</span>
                  <span><strong>No fractionalization</strong> of $10M+ assets</span>
                </li>
              </ul>
            </div>
          </div>

          <div class="mt-12 bg-yellow-50 border-l-4 border-yellow-400 p-6 rounded-lg">
            <p class="text-lg text-gray-800">
              <strong>Market Gap:</strong> GIFT City has built the infrastructure (FCSS settlement, IFSCA RWA framework) but
              <span class="text-yellow-700 font-semibold"> lacks an operating multi-asset platform</span> to execute policy intent.
              Zoniqx addresses securities only — real estate, commodities, infrastructure remain untouched.
            </p>
          </div>
        </div>
      </section>

      <!-- Solution Section -->
      <section id="solution" class="py-20 bg-white">
        <div class="max-w-7xl mx-auto px-4">
          <div class="text-center mb-16">
            <h2 class="text-4xl font-bold text-gray-900 mb-4">The Austial Solution</h2>
            <p class="text-xl text-gray-600 max-w-3xl mx-auto">
              Full-stack, IFSCA-compliant RWA tokenization platform with registered-form ownership and FCSS-linked settlement
            </p>
          </div>

          <!-- Solution Features -->
          <div class="grid md:grid-cols-3 gap-8 mb-16">
            <div class="bg-gradient-to-br from-blue-50 to-blue-100 rounded-2xl p-8 hover:shadow-xl transition">
              <div class="text-4xl mb-4">🪙</div>
              <h3 class="text-xl font-bold mb-3">Fractional Ownership</h3>
              <p class="text-gray-700">Convert $10M assets into $1,000 tokens. Investors subscribe to any quantity — no high minimums.</p>
            </div>

            <div class="bg-gradient-to-br from-green-50 to-green-100 rounded-2xl p-8 hover:shadow-xl transition">
              <div class="text-4xl mb-4">🔐</div>
              <h3 class="text-xl font-bold mb-3">Registered-Form Holdings</h3>
              <p class="text-gray-700">Identity-keyed ownership (not bearer tokens). Survives any IFSCA regulatory outcome.</p>
            </div>

            <div class="bg-gradient-to-br from-purple-50 to-purple-100 rounded-2xl p-8 hover:shadow-xl transition">
              <div class="text-4xl mb-4">⚡</div>
              <h3 class="text-xl font-bold mb-3">5-6 Sec Settlement</h3>
              <p class="text-gray-700">FCSS-linked USD funding/payout via IBU banking rail. Hours, not days.</p>
            </div>

            <div class="bg-gradient-to-br from-yellow-50 to-yellow-100 rounded-2xl p-8 hover:shadow-xl transition">
              <div class="text-4xl mb-4">✅</div>
              <h3 class="text-xl font-bold mb-3">KYC-First Architecture</h3>
              <p class="text-gray-700">No transaction possible without KYC_VERIFIED state. Database-enforced compliance.</p>
            </div>

            <div class="bg-gradient-to-br from-red-50 to-red-100 rounded-2xl p-8 hover:shadow-xl transition">
              <div class="text-4xl mb-4">📊</div>
              <h3 class="text-xl font-bold mb-3">7-Year Audit Trail</h3>
              <p class="text-gray-700">Append-only ledger. Every mutation logged. IFSCA reporting built-in.</p>
            </div>

            <div class="bg-gradient-to-br from-indigo-50 to-indigo-100 rounded-2xl p-8 hover:shadow-xl transition">
              <div class="text-4xl mb-4">🏢</div>
              <h3 class="text-xl font-bold mb-3">Multi-Asset Scope</h3>
              <p class="text-gray-700">Securities + Real Estate + Commodities + Infrastructure + IP. Broader than competitors.</p>
            </div>
          </div>

          <!-- Investor Flywheel -->
          <div class="gradient-bg rounded-2xl p-12 text-white">
            <h3 class="text-3xl font-bold mb-8 text-center">Complete Investor Flywheel (Live in MVP)</h3>
            <div class="grid md:grid-cols-5 gap-4">
              <div class="text-center">
                <div class="bg-white bg-opacity-20 rounded-full w-16 h-16 flex items-center justify-center text-2xl mx-auto mb-3">1</div>
                <h4 class="font-semibold mb-2">Funding</h4>
                <p class="text-sm text-blue-200">USD wire → IBU → FCSS → Account funded</p>
              </div>
              <div class="text-center">
                <div class="bg-white bg-opacity-20 rounded-full w-16 h-16 flex items-center justify-center text-2xl mx-auto mb-3">2</div>
                <h4 class="font-semibold mb-2">Discovery</h4>
                <p class="text-sm text-blue-200">Browse assets → View prospectus → 6-type disclosure</p>
              </div>
              <div class="text-center">
                <div class="bg-white bg-opacity-20 rounded-full w-16 h-16 flex items-center justify-center text-2xl mx-auto mb-3">3</div>
                <h4 class="font-semibold mb-2">Subscription</h4>
                <p class="text-sm text-blue-200">Lock funds → KYC gate → Allocation confirmed</p>
              </div>
              <div class="text-center">
                <div class="bg-white bg-opacity-20 rounded-full w-16 h-16 flex items-center justify-center text-2xl mx-auto mb-3">4</div>
                <h4 class="font-semibold mb-2">Holdings</h4>
                <p class="text-sm text-blue-200">TokenHolding created → Portfolio tracking → NAV updates</p>
              </div>
              <div class="text-center">
                <div class="bg-white bg-opacity-20 rounded-full w-16 h-16 flex items-center justify-center text-2xl mx-auto mb-3">5</div>
                <h4 class="font-semibold mb-2">Redemption</h4>
                <p class="text-sm text-blue-200">Request payout → Approval → USD back via FCSS</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- Pitch Deck Section -->
      <section id="pitch" class="py-20 gradient-bg">
        <div class="max-w-5xl mx-auto px-4 text-center text-white">
          <h2 class="text-4xl font-bold mb-6">Young Builders Program Pitch</h2>
          <p class="text-xl mb-8 text-blue-100 max-w-3xl mx-auto">
            Complete application with problem analysis, validation, regulatory pathway, and financial projections
          </p>

          <div class="bg-white bg-opacity-10 backdrop-blur-lg rounded-2xl p-8 mb-8">
            <div class="grid md:grid-cols-2 gap-8 text-left">
              <div>
                <h3 class="text-2xl font-bold mb-4">Pitch Snapshot</h3>
                <ul class="space-y-2 text-blue-100">
                  <li>✅ <strong>Stage:</strong> MVP Complete</li>
                  <li>✅ <strong>Track:</strong> BFSI Innovation</li>
                  <li>✅ <strong>Commitment:</strong> Full-Time</li>
                  <li>✅ <strong>TAM:</strong> $10-50B by 2030</li>
                </ul>
              </div>
              <div>
                <h3 class="text-2xl font-bold mb-4">Key Validation</h3>
                <ul class="space-y-2 text-blue-100">
                  <li>✓ 8 Customer Interviews</li>
                  <li>✓ 24 Entities, 100+ Tests</li>
                  <li>✓ Live Deployment</li>
                  <li>✓ IFSCA Compliance Mapped</li>
                </ul>
              </div>
            </div>
          </div>

          <a routerLink="/login" class="bg-white text-blue-900 px-12 py-4 rounded-lg font-bold text-lg inline-block hover:bg-blue-50 transition">
            Launch App & Explore
          </a>
        </div>
      </section>

      <!-- CTA Section -->
      <section class="py-20 bg-white">
        <div class="max-w-5xl mx-auto px-4 text-center">
          <h2 class="text-4xl font-bold mb-6 text-gray-900">Ready to Explore?</h2>
          <p class="text-xl text-gray-600 mb-8">Try the live MVP or schedule a demo with our team</p>

          <div class="flex flex-col sm:flex-row gap-4 justify-center">
            <a routerLink="/register" class="gradient-bg text-white px-10 py-4 rounded-lg font-semibold text-lg hover:opacity-90 transition">
              Create Free Account
            </a>
            <a href="mailto:team@austial.com" class="border-2 border-blue-600 text-blue-600 px-10 py-4 rounded-lg font-semibold text-lg hover:bg-blue-50 transition">
              Schedule a Call
            </a>
          </div>

          <div class="mt-12 grid md:grid-cols-3 gap-8 text-left">
            <div>
              <h4 class="font-bold text-lg mb-2">Test Credentials</h4>
              <p class="text-sm text-gray-600">Investor: investor&#64;test.com / password123</p>
              <p class="text-sm text-gray-600">Admin: admin&#64;test.com / password123</p>
            </div>
            <div>
              <h4 class="font-bold text-lg mb-2">Try These Flows</h4>
              <p class="text-sm text-gray-600">Auth → KYC → Subscribe → View Holdings → Redeem</p>
              <p class="text-sm text-gray-600">Admin Dashboard → Approve KYC → Monitor AML Alerts</p>
            </div>
            <div>
              <h4 class="font-bold text-lg mb-2">Contact</h4>
              <p class="text-sm text-gray-600">team&#64;austial.com</p>
              <p class="text-sm text-gray-600">Bengaluru → GIFT City Q1 2027</p>
            </div>
          </div>
        </div>
      </section>

      <!-- Footer -->
      <footer class="bg-gray-900 text-white py-12">
        <div class="max-w-7xl mx-auto px-4">
          <div class="text-center">
            <h3 class="text-2xl font-bold gradient-text mb-4">AUSTIAL</h3>
            <p class="text-gray-400 text-sm mb-4">IFSCA-compliant RWA tokenization platform for GIFT City IFSC</p>
            <p class="text-sm text-gray-400">© 2026 Austial. Built with ❤️ for GIFT City. Regulated by IFSCA. Powered by Austial Framework.</p>
            <p class="mt-2 text-sm text-gray-500">Stage: MVP Complete | Track: BFSI Innovation | Seeking: Young Builders Residency Q1 2027</p>
          </div>
        </div>
      </footer>
    </div>
  `,
  styles: [`
    .gradient-bg {
      background: linear-gradient(135deg, #0B4F6C 0%, #01BAEF 100%);
    }

    .gradient-text {
      background: linear-gradient(135deg, #01BAEF 0%, #0B4F6C 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
    }

    .card-hover {
      transition: all 0.3s ease;
    }

    .card-hover:hover {
      transform: translateY(-8px);
      box-shadow: 0 20px 40px rgba(1, 186, 239, 0.2);
    }
  `]
})
export class LandingComponent {}
